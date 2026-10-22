"""Independent matrix/hash audit including the frozen protocol's adaptive QC."""
import argparse
from datetime import datetime
import gzip
import json
import math
from pathlib import Path
import sqlite3

from constitution_distance.core import digest
from constitution_distance.exploratory import CANARY,CONDITIONS,resume_canary_items,verify_manifest
from verify_granite_exploratory_batch import read


def verify(batch):
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m);rid=digest(m)
    out=Path('results/granite-exploratory')/f'batch-{batch:04d}';root=Path('/workspace/work/granite-exploratory')/rid
    cs=m['constitution_order'];ids=m['batches'][batch-1]['scenario_ids'];n=len(ids);p=[]
    for name,_,_ in CONDITIONS:
        rows,cols,v=read(out/('probabilities-'+name+'.csv'));assert rows==cs and cols==ids;p.append(v)
    _,_,q=read(out/'probabilities-counterbalanced.csv');error=0.
    for c in range(24):
        for s in range(n):assert abs(q[c][s]-math.fsum(p[k][c][s] for k in range(4))/4)<1e-12
    for name in ['A_primary','B_secondary','C_canonical']:
        _,_,summed=read(out/('distances-'+name+'-summed-l1.csv'));_,_,normalized=read(out/('distances-'+name+'-normalized-l1.csv'))
        for c in range(24):
            for d in range(24):
                if name=='A_primary':expected=math.fsum(abs(q[c][s]-q[d][s]) for s in range(n))
                elif name=='B_secondary':expected=math.fsum(abs(p[k][c][s]-p[k][d][s]) for k in range(4) for s in range(n))/4
                else:expected=math.fsum(abs(p[0][c][s]-p[0][d][s]) for s in range(n))
                error=max(error,abs(expected-summed[c][d]),abs(expected/n-normalized[c][d]))
                assert error<1e-12 and normalized[c][d]>=0 and normalized[c][d]==normalized[d][c]
                if c==d:assert summed[c][d]==normalized[c][d]==0
    plan={tuple(r['pair']):r for r in map(json.loads,gzip.open('data/granite-exploratory/task-plan.jsonl.gz','rt')) if r['batch']==batch}
    records=list(map(json.loads,gzip.open(out/'responses.jsonl.gz','rt')));seen=set();adaptive=0
    for r in records:
        pair=tuple(r['item']['pair']);assert pair not in seen;seen.add(pair)
        assert r['request_hash']==digest(r['request']) and r['prompt_hash']==digest(r['request']['messages'])
        if pair in plan:
            assert r['request_hash']==plan[pair]['request_hash'] and r['prompt_hash']==plan[pair]['prompt_hash']
        else:
            assert pair[0]==CANARY and pair[1].startswith(f'b{batch:04d}-resume') and pair[2]==0
            ordinal=int(pair[1].split('-')[1].removeprefix('resume'))
            expected=next(i for i in resume_canary_items(m,batch,ordinal) if tuple(i['pair'])==pair)
            assert r['request']==expected['request'] and r['item']['expected']==expected['expected'];adaptive+=1
        assert r['response']['model']==m['settings']['model'] and r['response']['provider']=='Cloudflare'
        assert all(math.isfinite(r['result'][k]) for k in ['logp0','logp1']) and 0<=r['result']['p_to_do']<=1
    assert set(plan)<=seen and len(seen)==len(plan)+adaptive
    initial=json.load(gzip.open(out/'initial-stopped-attempts.json.gz','rt'))
    final=json.load(gzip.open(out/'attempts.json.gz','rt'));byid={a['id']:a for a in final}
    preserved=[a for a in initial if a['state']=='valid']
    assert all(byid[a['id']]==a for a in preserved)
    assert {a['id'] for a in preserved}<={r['attempt_id'] for r in records}
    db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True)
    try:
        assert db.execute('SELECT cap FROM settings').fetchone()[0]==10_000_000_000
        assert db.execute('SELECT cap,primary_cap FROM dispatch_stages WHERE id=?',(f'batch-{batch:04d}',)).fetchone()==(1_000_000_000,2000)
        assert db.execute("SELECT COUNT(*) FROM attempts WHERE state='reserved'").fetchone()[0]==0
        stages=[r[0] for r in db.execute('SELECT id FROM dispatch_stages ORDER BY id')];assert max(stages)==f'batch-{batch:04d}'
        assert db.execute('SELECT MAX(n) FROM (SELECT COUNT(*) n FROM attempts GROUP BY run,cid,sid,replica)').fetchone()[0]<=3
    finally:db.close()
    result={'status':'PASS','scope':f'BATCH_{batch}_ONLY','scenario_count':n,'scheduled_request_hash_matches':len(plan),
       'adaptive_resume_canary_requests_verified_against_frozen_rule':adaptive,'valid_records':len(records),
       'maximum_independent_A_B_C_error':error,'pre_interrupt_valid_attempts_preserved_unchanged':len(preserved),
       'original_global_cap_usd':10,'stage_cap_usd':1,'registered_stages':stages,'no_inflight_reservations':True,'later_stages_dispatched':False}
    (out/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    # Preserve the legacy export, then correct its latest-invocation timing and adaptive-QC accounting.
    legacy=out/'batch-report-latest-invocation.json'
    if legacy.exists():latest=json.loads(legacy.read_text())
    else:
        latest=json.loads((out/'batch-report.json').read_text());legacy.write_text(json.dumps(latest,indent=2)+'\n')
    invocations={}
    for f in (root/f'batch-{batch:04d}').glob('execution-*.json'):
        v=json.loads(f.read_text());key=v['started_at']
        if key not in invocations or v['elapsed_seconds_this_invocation']>invocations[key]['elapsed_seconds_this_invocation']:invocations[key]=v
    elapsed=sum(v['elapsed_seconds_this_invocation'] for v in invocations.values());progress=json.loads(Path(f'results/granite-exploratory/progress-after-batch-{batch:04d}.json').read_text())
    latest.update({'dispatch_invocations':len(invocations),'elapsed_seconds_latest_invocation':latest['elapsed_seconds'],
        'elapsed_seconds':elapsed,'valid_evaluations_per_second':len(records)/elapsed,
        'primary_evaluations_per_second':latest['valid']['primary']/elapsed,
        'wall_seconds_first_dispatch_to_final_snapshot':(max(datetime.fromisoformat(v['snapshot_at']) for v in invocations.values())-min(datetime.fromisoformat(k) for k in invocations)).total_seconds(),
        'remaining':progress['remaining'],'estimated_remaining_cost_usd_at_observed_token_usage':progress['estimated_remaining_cost_usd'],
        'estimated_total_cost_usd':progress['estimated_final_cost_usd'],'estimated_remaining_inference_seconds_at_observed_rate':progress['estimated_remaining_active_inference_seconds'],
        'estimated_completion_basis':'Cumulative observed usage, conservative failed-attempt charges, and both invocation histories; scheduled QC excludes extra resume QC.',
        'adaptive_resume_canaries':adaptive,'billed_usage_complete':all(a['actual_cost'] is not None for a in final),
        'unknown_billing_attempts':sum(a['actual_cost'] is None for a in final),
        'prompt_tokens_reported_by_responses':latest['prompt_tokens_all_attempts'],
        'completion_tokens_reported_by_responses':latest['completion_tokens_all_attempts'],
        'prompt_tokens_all_attempts':None,'completion_tokens_all_attempts':None,
        'mean_recorded_attempt_lifetime_seconds':latest['mean_attempt_latency_seconds'],'mean_attempt_latency_seconds':None,
        'usage_latency_note':'Transport failures lack usage; manual settlement finish timestamps are not provider latency. Full original reservations remain charged conservatively.'})
    (out/'batch-report.json').write_text(json.dumps(latest,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);a=p.parse_args();print(json.dumps(verify(a.batch),indent=2))
