"""Independent offline checks of A/B/C exports, frozen requests, and caps."""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path
import sqlite3

from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE,CANARY,CONDITIONS,verify_manifest


def read(path):
    rows=list(csv.reader(path.open()))
    return [r[0] for r in rows[1:]],rows[0][1:],[[float(x) for x in r[1:]] for r in rows[1:]]


def verify(batch):
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m);rid=digest(m)
    out=Path('results/granite-exploratory')/f'batch-{batch:04d}';root=Path('/workspace/work/granite-exploratory')/rid
    ids=m['batches'][batch-1]['scenario_ids'];cs=m['constitution_order'];n=len(ids);p=[]
    for name,_,_ in CONDITIONS:
        rows,cols,v=read(out/('probabilities-'+name+'.csv'));assert rows==cs and cols==ids;p.append(v)
    _,_,q=read(out/'probabilities-counterbalanced.csv');error=0.
    for c in range(24):
        for s in range(n):assert abs(q[c][s]-math.fsum(p[k][c][s] for k in range(4))/4)<1e-12
    for name in ['A_primary','B_secondary','C_canonical']:
        _,_,summed=read(out/('distances-'+name+'-summed-l1.csv'))
        _,_,normalized=read(out/('distances-'+name+'-normalized-l1.csv'))
        for c in range(24):
            for d in range(24):
                if name=='A_primary':expected=math.fsum(abs(q[c][s]-q[d][s]) for s in range(n))
                elif name=='B_secondary':expected=math.fsum(abs(p[k][c][s]-p[k][d][s]) for k in range(4) for s in range(n))/4
                else:expected=math.fsum(abs(p[0][c][s]-p[0][d][s]) for s in range(n))
                error=max(error,abs(expected-summed[c][d]),abs(expected/n-normalized[c][d]))
                assert abs(expected-summed[c][d])<1e-12 and abs(expected/n-normalized[c][d])<1e-12
                assert normalized[c][d]>=0 and normalized[c][d]==normalized[d][c]
    plan={}
    for line in gzip.open('data/granite-exploratory/task-plan.jsonl.gz','rt'):
        row=json.loads(line)
        if row['batch']==batch:plan[tuple(row['pair'])]=row
    records=[json.loads(s) for s in gzip.open(out/'responses.jsonl.gz','rt')]
    seen=set()
    for row in records:
        pair=tuple(row['item']['pair']);assert pair not in seen;seen.add(pair)
        assert row['request_hash']==digest(row['request'])==plan[pair]['request_hash']
        assert row['prompt_hash']==digest(row['request']['messages'])==plan[pair]['prompt_hash']
        assert row['response']['model']==m['settings']['model'] and row['response']['provider']=='Cloudflare'
        assert all(math.isfinite(row['result'][k]) for k in ['logp0','logp1'])
        assert 0<=row['result']['p_to_do']<=1
    assert seen==set(plan)
    db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True)
    try:
        cap=db.execute('SELECT cap FROM settings').fetchone()[0];assert cap==10_000_000_000
        stage=f'batch-{batch:04d}';stagecap=db.execute('SELECT cap FROM dispatch_stages WHERE id=?',(stage,)).fetchone()[0];assert stagecap==1_000_000_000
        assert db.execute("SELECT COUNT(*) FROM attempts WHERE state='reserved'").fetchone()[0]==0
        max_attempts=db.execute('SELECT MAX(n) FROM (SELECT COUNT(*) n FROM attempts GROUP BY run,cid,sid,replica)').fetchone()[0];assert max_attempts<=3
        stages=[s[0] for s in db.execute('SELECT id FROM dispatch_stages ORDER BY id')]
        assert max(stages)<=stage
    finally:db.close()
    result={'status':'PASS','scope':f'BATCH_{batch}_ONLY','scenario_count':n,'complete_request_hash_matches':len(records),
        'maximum_independent_A_B_C_error':error,'experiment_cap_usd':10,'stage_cap_usd':1,
        'max_attempts_observed_for_one_task':max_attempts,'registered_stages':stages,
        'no_inflight_reservations':True,'later_stages_dispatched':False,'api_requests_for_verification':0}
    (out/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);a=p.parse_args();print(json.dumps(verify(a.batch),indent=2))
