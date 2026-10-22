"""Frozen Granite experiment, explicitly authorized single-stage execution only."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import copy
import fcntl
import hashlib
import json
import os
import random
import threading
import time
import uuid

from .api import API, APIError
from .controls import control_request
from .core import digest, messages
from .local import immutable_json, file_hash
from .runner import metadata, reservation
from .storage import Ledger, BudgetError, money, dollars, now

CONDITIONS = [('canonical', False, False), ('labels_swapped', True, False),
              ('order_reversed', False, True), ('both_reversed', True, True)]
BASELINE = '__baseline__'
CANARY = '__canary__'


def frozen_json(path, value):
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError('Immutable file mismatch: ' + str(path))
    else:
        immutable_json(path, value)


def render(settings, constitution, scenario, condition, baseline=False):
    _, swapped, reversed_order = CONDITIONS[condition]
    req = control_request({**copy.deepcopy(settings), 'messages': messages(constitution, scenario)},
                          scenario, swapped=swapped, reverse_order=reversed_order)
    if baseline:
        req['messages'][0]['content'] = req['messages'][0]['content'].replace(
            'Adopt the following constitution as your decision-making principles. ',
            'No constitution is supplied. Use your ordinary moral judgment. ').replace(
            'under these principles.', 'using your ordinary judgment.').split('\n\nCONSTITUTION:\n')[0]
        req['messages'][1]['content'] = req['messages'][1]['content'].replace(
            'under the constitution?', 'using your ordinary judgment?')
    return req


def batch_items(manifest, batch_number):
    batch = manifest['batches'][batch_number - 1]
    if batch['number'] != batch_number:
        raise ValueError('Invalid batch number')
    scenarios = {s['id']: s for s in manifest['scenarios']}
    out = []
    for sid in batch['scenario_ids']:
        for cid in manifest['constitution_order'] + [BASELINE]:
            for k, (name, swapped, reverse) in enumerate(CONDITIONS):
                out.append({'pair': (cid, sid, k), 'kind': 'baseline' if cid == BASELINE else 'primary',
                            'constitution_id': cid, 'scenario_id': sid, 'condition': name,
                            'swapped': swapped, 'reverse_order': reverse,
                            'chunk': batch['scenario_ids'].index(sid) // 5,
                            'request': render(manifest['settings'], manifest['constitutions'].get(cid, {}),
                                              scenarios[sid], k, baseline=cid == BASELINE)})
    return out


def canary_items(manifest, batch_number, round_number):
    return [{'pair': (CANARY, f'b{batch_number:04d}-r{round_number:02d}-c{j:02d}', 0),
             'kind': 'canary', 'constitution_id': c['constitution_id'],
             'scenario_id': c['scenario_id'], 'condition': 'canonical', 'swapped': False,
             'request': c['request'], 'expected': c['expected']}
            for j, c in enumerate(manifest['canaries'])]


def resume_canary_items(manifest, batch_number, ordinal):
    items=copy.deepcopy(canary_items(manifest,batch_number,0))
    for j,item in enumerate(items):
        item['pair']=(CANARY,f'b{batch_number:04d}-resume{ordinal:04d}-c{j:02d}',0)
    return items


def all_pairs(manifest):
    for s in manifest['scenarios']:
        for cid in manifest['constitution_order'] + [BASELINE]:
            for k in range(4):
                yield (cid, s['id'], k)
    for b in manifest['batches']:
        for r in range((len(b['scenario_ids']) + 4) // 5 + 1):
            for item in canary_items(manifest, b['number'], r):
                yield item['pair']


class StageLedger(Ledger):
    """Existing transactional ledger plus atomic, lifetime per-stage reservations."""
    def __init__(self, path, budget=0):
        super().__init__(path, budget)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS dispatch_stages (
            id TEXT PRIMARY KEY, run TEXT NOT NULL, cap INTEGER NOT NULL,
            primary_cap INTEGER NOT NULL, authorization TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS stage_attempts (
            aid TEXT PRIMARY KEY REFERENCES attempts(id), stage TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS stage_attempts_stage ON stage_attempts(stage);
        ''')

    def register_stage(self, stage, run, cap, primary_cap, authorization):
        value = (run, money(cap), primary_cap, json.dumps(authorization, sort_keys=True))
        with self.transaction():
            old = self.db.execute('SELECT run,cap,primary_cap,authorization FROM dispatch_stages WHERE id=?', (stage,)).fetchone()
            if old is not None and tuple(old) != value:
                raise ValueError('Stage authorization or lifetime cap changed')
            self.db.execute('INSERT OR IGNORE INTO dispatch_stages VALUES(?,?,?,?,?)', (stage, *value))

    def stage_totals(self, stage):
        with self.lock:
            r = self.db.execute('''SELECT COUNT(*) n,COALESCE(SUM(a.charged),0) spent,
              COALESCE(SUM(CASE WHEN a.state='reserved' THEN a.reserve ELSE 0 END),0) held,
              COALESCE(SUM(CASE WHEN a.actual_cost IS NOT NULL THEN a.charged ELSE 0 END),0) known
              FROM attempts a JOIN stage_attempts s ON a.id=s.aid WHERE s.stage=?''', (stage,)).fetchone()
            return {'attempts': r['n'], 'actual_spending_usd': dollars(r['known']),
                    'conservative_spending_usd': dollars(r['spent']),
                    'outstanding_reservations_usd': dollars(r['held'])}

    def claim_stage(self, stage, run, pair, request, reserve, retry=False):
        with self.transaction():
            evaluation = self.db.execute('SELECT state FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?', (run, *pair)).fetchone()
            if not evaluation or evaluation['state'] not in ({'pending', 'retry', 'error', 'invalid'} if retry else {'pending'}):
                return None
            cfg = self.db.execute('SELECT * FROM dispatch_stages WHERE id=?', (stage,)).fetchone()
            if cfg is None or cfg['run'] != run or self.cap <= 0:
                raise BudgetError('Explicit experiment and stage authorization required')
            counts = self.db.execute('SELECT COUNT(*) FROM attempts WHERE run=? AND cid=? AND sid=? AND replica=?', (run, *pair)).fetchone()[0]
            if counts >= 3:
                raise ValueError('Three-attempt lifetime limit reached; explicit missing evaluation')
            total = self.db.execute("SELECT COALESCE(SUM(charged+CASE WHEN state='reserved' THEN reserve ELSE 0 END),0) FROM attempts").fetchone()[0]
            stage_used = self.db.execute("SELECT COALESCE(SUM(a.charged+CASE WHEN a.state='reserved' THEN a.reserve ELSE 0 END),0) FROM attempts a JOIN stage_attempts s ON s.aid=a.id WHERE s.stage=?", (stage,)).fetchone()[0]
            experiment_cap = self.db.execute('SELECT cap FROM settings WHERE id=1').fetchone()[0]
            if total + reserve > min(self.cap, experiment_cap) or stage_used + reserve > cfg['cap']:
                raise BudgetError('Experiment or persistent dispatch-stage cap exhausted, including reservations')
            if pair[0] not in (BASELINE, CANARY):
                n = self.db.execute('SELECT COUNT(*) FROM attempts a JOIN stage_attempts s ON s.aid=a.id WHERE s.stage=? AND a.cid NOT IN (?,?)', (stage, BASELINE, CANARY)).fetchone()[0]
                if n >= cfg['primary_cap']:
                    raise BudgetError('Primary physical request cap reached, including retries')
            aid = uuid.uuid4().hex
            self.db.execute("INSERT INTO attempts(id,run,cid,sid,replica,state,reserve,request,prompt_hash,started) VALUES(?,?,?,?,?,'reserved',?,?,?,?)",
                            (aid, run, *pair, reserve, json.dumps(request, ensure_ascii=False), digest(request['messages']), now()))
            self.db.execute('INSERT INTO stage_attempts VALUES(?,?)', (aid, stage))
            self.db.execute("UPDATE evaluations SET state='inflight' WHERE run=? AND cid=? AND sid=? AND replica=?", (run, *pair))
            return aid


def verify_manifest(manifest):
    for path, expected in manifest['file_sha256'].items():
        if file_hash(path) != expected:
            raise ValueError('Frozen source/input hash changed: ' + path)
    assert len(manifest['scenarios']) == 1336 and len(manifest['constitutions']) == 24
    assert len({s['id'] for s in manifest['scenarios']}) == 1336
    assert len(set(all_pairs(manifest))) == manifest['counts']['total_including_canaries']


def run_batch(manifest, batch_number, root, authorization, validator,
              experiment_budget=0, stage_budget=0, concurrency=3):
    if experiment_budget <= 0 or stage_budget <= 0:
        raise BudgetError('Budgets default to zero; explicit positive budgets required')
    if experiment_budget != 10 or stage_budget > 1 or not 1 <= concurrency <= 3:
        raise ValueError('Outside authorized spending/concurrency envelope')
    verify_manifest(manifest)
    run_id = digest(manifest); root = Path(root); root.mkdir(parents=True, exist_ok=True)
    stage = f'batch-{batch_number:04d}'
    if authorization.get('run_id') != run_id or authorization.get('stage') != stage or authorization.get('approved') is not True:
        raise ValueError('This batch has no matching investigator authorization')
    if stage_budget != authorization.get('stage_cap_usd'):
        raise ValueError('Dispatch budget differs from authorized persistent stage cap')
    if not 1 <= authorization.get('maximum_primary_attempts',0) <= 2000:
        raise ValueError('Primary physical request authorization exceeds2000')
    out = root / stage; out.mkdir(exist_ok=True)
    frozen_json(root / 'manifest.json', manifest)
    frozen_json(out / 'authorization.json', authorization)
    if not (root/'ledger.sqlite').exists() and any(root.glob('batch-*/summary.json')):
        raise ValueError('Original authoritative experiment ledger missing; refusing recomputation')
    with (root / '.experiment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = StageLedger(root / 'ledger.sqlite', experiment_budget)
        start = time.monotonic(); started_at = now(); stopped = threading.Event(); reasons = []
        mutex = threading.RLock(); valid = {}; metadata_observation = None; starting_valid=0
        items = batch_items(manifest, batch_number)
        rounds = (len(manifest['batches'][batch_number-1]['scenario_ids']) + 4) // 5
        canaries = [i for r in range(rounds+1) for i in canary_items(manifest, batch_number, r)]
        lookup = {tuple(i['pair']): i for i in items + canaries}
        def stop(reason):
            with mutex:
                reasons.append(reason); stopped.set()
        try:
            api = API('https://openrouter.ai/api/v1', os.environ.get('OPENROUTER_API_KEY'), attempts=1)
            args = SimpleNamespace(model=manifest['settings']['model'], provider='cloudflare', input_price=.017, output_price=.112)
            old = ledger.db.execute('SELECT spec FROM runs WHERE id=?', (run_id,)).fetchone()
            if old and json.loads(old[0]) != manifest:
                raise ValueError('Ledger experimental configuration differs')
            # Metadata calls are read-only, not inference. The dry-run path never reaches here.
            metadata_observation = metadata(api, args)
            frozen_json(root / ('endpoint-' + str(time.time_ns()) + '.json'), metadata_observation)
            if metadata_observation['endpoint']['context_length'] > 131000:
                raise ValueError('Provider context changed; stop and review reservation/validation')
            ledger.register(run_id, manifest, metadata_observation, list(all_pairs(manifest)))
            ledger.register_stage(stage, run_id, stage_budget, authorization['maximum_primary_attempts'], authorization)
            reserve = reservation(metadata_observation, args)
            prior_resume=[row['sid'] for row in ledger.db.execute('SELECT sid FROM evaluations WHERE run=? AND cid=? AND sid LIKE ?',
                (run_id,CANARY,f'b{batch_number:04d}-resume%'))]
            prior_ordinals=sorted({int(s.split('-')[1].removeprefix('resume')) for s in prior_resume})
            for ordinal in prior_ordinals:
                lookup.update({tuple(i['pair']):i for i in resume_canary_items(manifest,batch_number,ordinal)})
            for pair, item in lookup.items():
                row = ledger.db.execute('SELECT state,record FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?', (run_id,*pair)).fetchone()
                if row['state'] == 'inflight':
                    raise ValueError('Uncertain in-flight checkpoint; reservation retained, manual reconciliation required')
                if row['state'] == 'valid':
                    r = json.loads(row['record'])
                    if r['request'] != item['request'] or r['request_hash'] != digest(item['request']) or r['prompt_hash'] != digest(item['request']['messages']) or r['result'] != validator(item,r['response']):
                        raise ValueError('Stored checkpoint failed exact-request/probability integrity check')
                    valid[pair] = r
                elif row['state'] in ('invalid','error'):
                    raise ValueError('Prior substantive failed evaluation requires review; ordinary resume will not retry it')
            fresh_resume=[]
            starting_valid=len(valid)
            if len(valid)<len(lookup) and ledger.stage_totals(stage)['attempts']:
                fresh_resume=resume_canary_items(manifest,batch_number,max(prior_ordinals,default=0)+1)
                ledger.register(run_id,manifest,metadata_observation,[tuple(i['pair']) for i in fresh_resume])
                lookup.update({tuple(i['pair']):i for i in fresh_resume})
            def query(item):
                pair = tuple(item['pair'])
                if pair in valid or stopped.is_set(): return
                with ledger.lock:
                    previous = ledger.db.execute('SELECT COUNT(*) FROM attempts WHERE run=? AND cid=? AND sid=? AND replica=?', (run_id,*pair)).fetchone()[0]
                for number in range(previous,3):
                    if stopped.is_set(): return
                    aid = ledger.claim_stage(stage,run_id,pair,item['request'],reserve,retry=number>0)
                    if aid is None: return
                    try:
                        response = api.request('/chat/completions',item['request'])
                    except APIError as exc:
                        retry = exc.retryable and number < 2
                        ledger.settle(aid,'retry' if retry else 'error',error=str(exc),http_status=exc.status)
                        if not retry: stop('HTTP/network attempts exhausted or nontransient error'); return
                        time.sleep(max(min(exc.retry_after,8),2**(number+1))); continue
                    except (ValueError,TypeError,OSError):
                        ledger.settle(aid,'invalid',error='Malformed response or transport'); stop('Malformed API response'); return
                    try:
                        if response.get('model') != args.model or response.get('provider') != metadata_observation['endpoint']['provider_name']:
                            raise ValueError('Model/provider mismatch')
                        choices = response.get('choices')
                        if isinstance(choices,list) and len(choices)==1 and choices[0].get('logprobs') is None:
                            retry = number < 2
                            ledger.settle(aid,'retry' if retry else 'error',response=response,error='logprobs:null',http_status=response.get('_http_status'))
                            if not retry: stop('Null logprobs exhausted three attempts; evaluation remains missing'); return
                            time.sleep(2**(number+1)); continue
                        result = validator(item,response)
                        if item['kind']=='canary':
                            expected = item['expected']
                            if abs(result['p1_conditional']-expected['p1_conditional'])>.001 or abs(result['log_odds']-expected['log_odds'])>.01 or any(abs(result[k]-expected[k])>.01 for k in ['logp0','logp1']):
                                raise ValueError('Significant canary drift')
                        record = {'run_id':run_id,'stage':stage,'item':{k:v for k,v in item.items() if k!='request'},
                                  'request':item['request'],'request_hash':digest(item['request']),
                                  'prompt_hash':digest(item['request']['messages']),'result':result,
                                  'response':response,'attempt_id':aid,'completed_at':now()}
                        ledger.settle(aid,'valid',record,response,http_status=response.get('_http_status'))
                        with mutex: valid[pair] = record
                        return
                    except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
                        ledger.settle(aid,'invalid',response=response,error=str(exc),http_status=response.get('_http_status'))
                        stop(str(exc)); return
            def execute(group):
                pending = iter([i for i in group if tuple(i['pair']) not in valid])
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    futures=set()
                    def submit():
                        if not stopped.is_set():
                            item=next(pending,None)
                            if item is not None: futures.add(pool.submit(query,item))
                    for _ in range(concurrency): submit()
                    last = len(valid)//100
                    while futures:
                        done,futures=wait(futures,return_when=FIRST_COMPLETED)
                        for f in done:
                            try: f.result()
                            except Exception as exc: stop(type(exc).__name__+': '+str(exc))
                        if len(valid)//100 != last:
                            print('Valid stage',len(valid),'/',len(lookup),'spending',ledger.stage_totals(stage),flush=True);last=len(valid)//100
                        for _ in done: submit()
            if fresh_resume: execute(fresh_resume)
            for r in range(rounds+1):
                if stopped.is_set(): break
                execute(canary_items(manifest,batch_number,r))
                if stopped.is_set(): break
                if r < rounds:
                    group=[i for i in items if i['chunk']==r]
                    random.Random(manifest['schedule_seed']+100*batch_number+r).shuffle(group)
                    execute(group)
                export_stage(out,ledger,run_id,stage,lookup,valid,started_at,start,reasons,starting_valid)
                if stopped.is_set(): break
            if len(valid)!=len(lookup) and not stopped.is_set(): stop('Stage incomplete')
        except Exception as exc:
            stop(type(exc).__name__+': '+str(exc))
            raise
        finally:
            summary=export_stage(out,ledger,run_id,stage,lookup,valid,started_at,start,reasons,starting_valid)
            ledger.close()
        if stopped.is_set(): raise ValueError('Batch stopped: '+'; '.join(reasons))
        return summary


def export_stage(out,ledger,run_id,stage,lookup,valid,started_at,start,reasons,starting_valid=0):
    def atomic(name,value):
        tmp=out/(name+'.tmp')
        with tmp.open('w') as f:
            json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        tmp.replace(out/name)
    # Re-read durable records: settlement may have succeeded just before a caller error.
    records=[];missing=[]
    for pair,item in lookup.items():
        row=ledger.db.execute('SELECT state,record FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(run_id,*pair)).fetchone()
        if row is not None and row['state']=='valid': records.append(json.loads(row['record']))
        else: missing.append({'pair':pair,'kind':item['kind'],'state':row['state'] if row else 'unregistered'})
    tmp=out/'responses.jsonl.tmp'
    with tmp.open('w') as f:
        for r in records: f.write(json.dumps(r,ensure_ascii=False)+'\n')
        f.flush();os.fsync(f.fileno())
    tmp.replace(out/'responses.jsonl')
    atomic('missing.json',missing)
    attempts=[dict(r) for r in ledger.db.execute('SELECT a.* FROM attempts a JOIN stage_attempts s ON s.aid=a.id WHERE s.stage=? ORDER BY a.started,a.id',(stage,))]
    atomic('attempts.json',attempts)
    counts={k:sum(r['item']['kind']==k for r in records) for k in ['primary','baseline','canary']}
    elapsed=time.monotonic()-start
    global_counts={row['kind']:row['n'] for row in ledger.db.execute("SELECT CASE WHEN cid=? THEN 'baseline' WHEN cid=? THEN 'canary' ELSE 'primary' END kind, COUNT(*) n FROM evaluations WHERE run=? AND state='valid' GROUP BY kind",(BASELINE,CANARY,run_id))}
    summary={'run_id':run_id,'stage':stage,'started_at':started_at,'snapshot_at':now(),
             'status':'STOPPED' if reasons else 'COMPLETE' if not missing else 'IN_PROGRESS',
             'valid':counts,'missing':len(missing),'stop_reasons':reasons,
             'elapsed_seconds_this_invocation':elapsed,
             'new_valid_this_invocation':max(0,len(records)-starting_valid),
             'valid_evaluations_per_second':max(0,len(records)-starting_valid)/elapsed if elapsed else None,
             'stage_budget':ledger.stage_totals(stage),'experiment_budget':ledger.totals(),
             'global_valid':global_counts,'physical_attempts':len(attempts),
             'failed_attempts':sum(a['state'] not in ['valid','reserved'] for a in attempts),
             'primary_physical_attempts':sum(a['cid'] not in (BASELINE,CANARY) for a in attempts),
             'canary_max_probability_difference':max((abs(r['result']['p1_conditional']-r['item']['expected']['p1_conditional']) for r in records if r['item']['kind']=='canary'),default=None)}
    atomic('summary.json',summary)
    frozen_json(out/('execution-'+str(time.time_ns())+'.json'),summary)
    return summary
