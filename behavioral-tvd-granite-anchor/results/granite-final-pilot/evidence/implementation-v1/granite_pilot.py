"""Independent final-pilot runner: immutable design, budgeted retries, stop-on-drift."""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from collections import deque
from decimal import Decimal
import json,os,threading,time
from pathlib import Path
from types import SimpleNamespace
from .api import API,APIError
from .core import digest
from .local import immutable_json
from .runner import metadata
from .storage import Ledger,money,now


def run_pilot(spec,validator,root,budget=0,workers=6):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    run_id=digest(spec);out=root/run_id;out.mkdir(exist_ok=True)
    configfile=out/'configuration.json'
    if configfile.exists():
        if json.loads(configfile.read_text())!=spec:raise ValueError('Immutable configuration mismatch')
    else:immutable_json(configfile,spec)
    items=spec['items'];lookup={(i['id'],'request',i['replica']):i for i in items}
    if len(lookup)!=len(items):raise ValueError('Duplicate evaluation slots')
    ledger=Ledger(root/'budget.sqlite',budget);api=API('https://openrouter.ai/api/v1',os.environ.get('OPENROUTER_API_KEY'),attempts=1)
    mutex=threading.RLock();stopped=threading.Event();errors=deque(maxlen=20);reason=[];known={};valid={}
    def stop(message):
        with mutex:
            reason.append(message);stopped.set()
    try:
        states=ledger.states(run_id)
        for pair,row in states.items():
            if row['state']=='valid':
                r=json.loads(row['record']);i=lookup[pair]
                if r['request']!=i['request'] or r['request_hash']!=digest(i['request']) or r['result']!=validator(i,r['response']):raise ValueError('Checkpoint integrity failed')
                valid[pair]=r;known[r['request_hash']]=r['result']
        settings=items[0]['request'];args=SimpleNamespace(model=settings['model'],provider=settings['provider']['only'][0],input_price=settings['provider']['max_price']['prompt'],output_price=settings['provider']['max_price']['completion'])
        if len(valid)<len(items):
            if budget<=0:raise ValueError('Explicit budget required')
            meta=metadata(api,args)
        else:meta=json.loads(ledger.db.execute('SELECT metadata FROM runs WHERE id=?',(run_id,)).fetchone()[0])
        ledger.register(run_id,spec,meta,list(lookup))
        reservation=money((Decimal(meta['endpoint']['context_length'])*Decimal(str(args.input_price))+Decimal(str(args.output_price)))/1_000_000*Decimal('1.10'))
        attempts=ledger.attempts(run_id);counts={p:sum((a['cid'],a['sid'],a['replica'])==p for a in attempts) for p in lookup}
        if any(row['state']=='inflight' for row in states.values()):raise ValueError('Uncertain in-flight checkpoint: stop and reconcile; reservation remains held')
        if any(row['state']=='invalid' for row in states.values()):raise ValueError('Prior invalid response requires review, not automatic retry')
        if (out/'STOP.json').exists():raise ValueError('Prior safety stop requires review; not automatically resumed')
        def query(item):
            pair=(item['id'],'request',item['replica']);req=item['request'];rh=digest(req)
            if req['provider']!=settings['provider'] or req['model']!=args.model:raise ValueError('Mixed model/provider configuration')
            for number in range(counts.get(pair,0),2):
                if stopped.is_set():return
                aid=ledger.claim(run_id,pair,req,reservation,retry_missing=number>0,max_requests=2*len(items))
                if aid is None:return
                try:response=api.request('/chat/completions',req)
                except APIError as exc:
                    ledger.settle(aid,'error',error=str(exc),http_status=exc.status)
                    with mutex:
                        errors.append(1)
                        if number>=1 or sum(errors)>=3:stop('Repeated HTTP/network failures; dispatch stopped')
                    if not exc.retryable:stop('Non-transient HTTP error')
                    if stopped.is_set() or not exc.retryable:return
                    time.sleep(max(min(exc.retry_after,8),2**(number+1)));continue
                except (ValueError,TypeError,OSError):
                    ledger.settle(aid,'invalid',error='Malformed API response');stop('Malformed response');return
                try:
                    if response.get('model')!=args.model or response.get('provider')!=meta['endpoint']['provider_name']:raise ValueError('Model/provider identity mismatch')
                    result=validator(item,response)
                    with mutex:
                        prior=known.get(rh)
                        if prior and (abs(result['p1_conditional']-prior['p1_conditional'])>.001 or abs(result['log_odds']-prior['log_odds'])>.01):raise ValueError('Unexpected numerical drift between identical requests')
                        expected=item.get('expected')
                        if expected and (abs(result['p1_conditional']-expected['p1_conditional'])>.001 or abs(result['log_odds']-expected['log_odds'])>.01):raise ValueError('Canary drift from earlier Granite comparison')
                        known[rh]=result;errors.append(0)
                    r={'run_id':run_id,'item':item,'request':req,'request_hash':rh,'prompt_hash':digest(req['messages']),'response':response,'result':result,'metadata':meta,'attempt_id':aid,'completed_at':now()}
                    ledger.settle(aid,'valid',r,response,http_status=response.get('_http_status'))
                    with mutex:valid[pair]=r
                    return
                except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
                    ledger.settle(aid,'invalid',response=response,error=str(exc),http_status=response.get('_http_status'));stop(str(exc));return
        pending=[i for i in items if (i['id'],'request',i['replica']) not in valid]
        try:
            # Single capability gate before bounded parallel dispatch.
            if pending:
                query(pending.pop(0))
                if stopped.is_set() or (items[0]['id'],'request',items[0]['replica']) not in valid:raise ValueError('Safety gate failed')
            with ThreadPoolExecutor(max_workers=workers) as pool:
                it=iter(pending);futures=set()
                def submit():
                    if not stopped.is_set():
                        item=next(it,None)
                        if item is not None:futures.add(pool.submit(query,item))
                for _ in range(workers):submit()
                last=-1
                while futures:
                    done,futures=wait(futures,return_when=FIRST_COMPLETED)
                    for f in done:
                        try:f.result()
                        except Exception as exc:stop(type(exc).__name__+': '+str(exc))
                    n=len(valid)
                    if n//50!=last:print('Valid',n,'/',len(items),'budget',ledger.totals(),flush=True);last=n//50
                    for _ in done:submit()
        finally:
            states=ledger.states(run_id)
            (out/'responses.jsonl').write_text(''.join(json.dumps(json.loads(row['record']),ensure_ascii=False)+'\n' for row in states.values() if row['state']=='valid'))
            # Scientific config/records immutable; exports reflect durable ledger, unique audit snapshot.
            stamp=str(time.time_ns())
            immutable_json(out/('execution-'+stamp+'.json'),{'run_id':run_id,'workers':workers,'valid':len(valid),'expected':len(items),'budget':ledger.totals(),'missing':[{'id':p[0],'replica':p[2],'state':row['state']} for p,row in states.items() if row['state']!='valid'],'attempts':ledger.attempts(run_id)})
            if stopped.is_set() and not (out/'STOP.json').exists():immutable_json(out/'STOP.json',{'reasons':reason,'at':now()})
        if stopped.is_set():raise ValueError('Safety stop: '+'; '.join(reason))
        if len(valid)!=len(items):raise ValueError('Pilot incomplete; missing evaluations retained')
        return {'run_id':run_id,'out':str(out),'valid':len(valid),'budget':ledger.totals()}
    finally:ledger.close()
