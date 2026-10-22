"""Budgeted auxiliary studies: exact requests, explicit validators, no hidden retries.

Uses the same durable reservation ledger as the primary runner, but supports
bounded JSON-output semantic screening as a separately identified study.
"""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from decimal import Decimal
import json
import os
from pathlib import Path

from .api import API, APIError
from .core import digest
from .runner import metadata, write_json
from .storage import Ledger, money, now, BudgetError


def run_study(name, items, validator, *, ledger_path, output, budget=0, concurrency=2):
    """One bounded attempt per item; invalid/uncertain entries are never fabricated."""
    from argparse import Namespace
    spec = {'name': name, 'items': items, 'validator_version': 1}
    run_id = digest(spec)
    out = Path(output); out.mkdir(parents=True, exist_ok=True)
    if (out/'manifest.json').exists() and json.loads((out/'manifest.json').read_text())['run_id']!=run_id:
        raise ValueError('Auxiliary output belongs to a different configuration')
    ledger = Ledger(ledger_path, budget)
    try:
        states = ledger.states(run_id)
        item_by={(i['id'],'request',i.get('replica',0)):i for i in items}
        for pair,row in states.items():
            if row['state']=='valid':
                record=json.loads(row['record']);item=item_by[pair]
                if (record['request']!=item['request'] or record['request_hash']!=digest(item['request'])
                    or record['prompt_hash']!=digest(item['request']['messages'])
                    or record['result']!=validator(item,record['response'])):
                    raise ValueError('Auxiliary checkpoint integrity mismatch')
        pending = [i for i in items if (i['id'], 'request', i.get('replica', 0)) not in states or
                   states[(i['id'], 'request', i.get('replica', 0))]['state'] == 'pending']
        if pending and budget <= 0:
            raise BudgetError('Auxiliary study requires an explicit nonzero shared budget')
        settings = items[0]['request']
        args = Namespace(model=settings['model'], provider=settings['provider']['only'][0],
            input_price=settings['provider']['max_price']['prompt'],
            output_price=settings['provider']['max_price']['completion'])
        api = API('https://openrouter.ai/api/v1', os.environ.get('OPENROUTER_API_KEY'), attempts=1)
        if pending:
            if not os.environ.get('OPENROUTER_API_KEY'):
                raise ValueError('Configure the network secret')
            meta = metadata(api, args)
            if any('seed' in i['request'] for i in pending) and 'seed' not in meta['endpoint'].get('supported_parameters',[]):
                raise ValueError('Pinned endpoint does not advertise seed support; no seeded requests dispatched')
        else:
            meta = json.loads(ledger.db.execute('SELECT metadata FROM runs WHERE id=?',(run_id,)).fetchone()[0])
        ledger.register(run_id, spec, meta, [(i['id'], 'request', i.get('replica',0)) for i in items])
        write_json(out/'manifest.json',{'run_id':run_id,'spec':spec,'metadata':meta,
                                      'ledger':str(Path(ledger_path).resolve()),'observed_at':now()})
        def query(item):
            request=item['request'];pair=(item['id'],'request',item.get('replica',0))
            if (request['model']!=args.model or request['provider']!=settings['provider']
                    or request['max_tokens']<1):
                raise ValueError('Study request model/provider/configuration mismatch')
            price=(Decimal(meta['endpoint']['context_length'])*Decimal(str(args.input_price))+
                   Decimal(request['max_tokens'])*Decimal(str(args.output_price)))/1_000_000*Decimal('1.10')
            aid=ledger.claim(run_id,pair,request,money(price),max_requests=len(items))
            if aid is None:return
            try:
                response=api.request('/chat/completions',request)
            except APIError as exc:
                ledger.settle(aid,'error',error=str(exc),http_status=exc.status);return
            except (ValueError,TypeError,OSError) as exc:
                ledger.settle(aid,'invalid',error='Malformed response: '+type(exc).__name__);return
            try:
                if response.get('model')!=args.model or response.get('provider')!=meta['endpoint']['provider_name']:
                    raise ValueError('Study identity mismatch')
                usage=response.get('usage',{})
                if not isinstance(usage.get('cost'),(int,float)) or isinstance(usage.get('cost'),bool):
                    raise ValueError('Missing actual cost')
                money(usage['cost'])
                if type(usage.get('prompt_tokens')) is not int or usage['prompt_tokens']>meta['endpoint']['context_length']:
                    raise ValueError('Invalid prompt usage')
                if type(usage.get('completion_tokens')) is not int or not 0<=usage['completion_tokens']<=request['max_tokens']:
                    raise ValueError('Invalid completion usage')
                result=validator(item,response)
            except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
                ledger.settle(aid,'invalid',response=response,error=str(exc),http_status=response.get('_http_status'));return
            record={'run_id':run_id,'item':item,'request':request,'request_hash':digest(request),
                'prompt_hash':digest(request['messages']),'response':response,'result':result,
                'metadata':meta,'attempt_id':aid,'completed_at':now()}
            ledger.settle(aid,'valid',record,response,http_status=response.get('_http_status'))
        failure=None
        try:
            if pending:
                gate=pending.pop(0);query(gate)
                if ledger.states(run_id)[(gate['id'],'request',gate.get('replica',0))]['state']!='valid':
                    raise ValueError('Auxiliary capability gate failed; no batch dispatched')
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                items_iter=iter(pending);futures=set()
                def submit():
                    item=next(items_iter,None)
                    if item is not None:futures.add(pool.submit(query,item))
                for _ in range(concurrency):submit()
                while futures:
                    done,futures=wait(futures,return_when=FIRST_COMPLETED)
                    for future in done:
                        try:future.result()
                        except Exception as exc:failure=failure or exc
                    if failure is None:
                        for _ in done:submit()
                    print(f'{name}: valid {sum(r["state"]=="valid" for r in ledger.states(run_id).values())}/{len(items)}',flush=True)
        except Exception as exc:
            failure=exc
        finally:
            states=ledger.states(run_id)
            records=[json.loads(r['record']) for r in states.values() if r['state']=='valid']
            (out/'responses.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records))
            write_json(out/'missing.json',[{'id':p[0],'replica':p[2],'state':r['state']} for p,r in states.items() if r['state']!='valid'])
            write_json(out/'attempts.json',ledger.attempts(run_id))
            write_json(out/'budget.json',ledger.totals())
        if failure:raise failure
        return records
    finally:
        ledger.close()
