"""Offline verification/accounting/backup for explicitly reactivated batches 4–5.

No dispatch or checkpoint mutation. Retains frozen scientific definitions and
checks actual answer-token distributions independently of their extraction code.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import sqlite3
import tarfile

import numpy as np
from constitution_distance.core import digest
from constitution_distance.exploratory import CONDITIONS, frozen_json, verify_manifest
from constitution_distance.local import file_hash
from verify_granite_exploratory_batch import read, verify


def finish(batch, scope_path=None):
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m)
    rid=digest(m);root=Path('/workspace/work/granite-exploratory')/rid;stage=f'batch-{batch:04d}'
    out=Path('results/granite-exploratory')/stage
    assert not (out/'preservation-manifest.json').exists(), 'Already finalized; inspect existing evidence instead of overwriting it'
    scope_path=Path(scope_path or 'configs/granite-exploratory-reactivations/batches-0004-0005.json')
    scope=json.loads(scope_path.read_text());group=scope['approved_execution_batches']
    assert group in [[4,5],[6,7,8],[9,10,11],[12,13,14]] and batch in group and scope['run_id']==rid
    prohibited=group[-1]+1
    assert not Path(f'configs/granite-exploratory-authorizations/batch-{prohibited:04d}.json').exists()
    authorizations=scope.get('authorization_files',scope.get('reactivates_original_conditional_authorizations'))
    for b in group:assert file_hash(authorizations[str(b)]['path'])==authorizations[str(b)]['sha256']
    report=json.loads((out/'batch-report.json').read_text())
    assert report['status']=='COMPLETE' and report['unresolved_evaluations']==0
    assert report['valid']=={'primary':1920,'baseline':80,'canary':30}
    assert json.loads((out/'prior-records-postcheck.json').read_text())['status']=='PASS'
    result=verify(batch)
    records=list(map(json.loads,gzip.open(out/'responses.jsonl.gz','rt')))
    attempts=json.load(gzip.open(out/'attempts.json.gz','rt'))
    by_pair={tuple(r['item']['pair']):r for r in records}
    assert len(attempts)==report['physical_attempts']
    for a in attempts:
        pair=(a['cid'],a['sid'],a['replica']);assert pair in by_pair and a['run']==rid
        assert digest(json.loads(a['request']))==by_pair[pair]['request_hash']
        assert a['prompt_hash']==by_pair[pair]['prompt_hash']
    assert sum(a['charged'] for a in attempts)<=1_000_000_000
    assert report['primary_physical_attempts']<=2000
    cs=m['constitution_order'];ids=m['batches'][batch-1]['scenario_ids'];values=np.full((4,24,20),np.nan)
    maxerr=0.;masses=[];qcdiffs=[];rawdiffs=[]
    for r in records:
        tokens=r['response']['choices'][0]['logprobs']['content'][0]['top_logprobs']
        logs={t['token']:t['logprob'] for t in tokens if t['token'] in ['0','1']};assert set(logs)=={'0','1'}
        for t in tokens:
            if t['token'] in logs:assert t['bytes']==[ord(t['token'])]
        a,b=math.exp(logs['0']),math.exp(logs['1']);q=b/(a+b)
        semantic=1-q if r['item'].get('swapped',False) else q
        calculated={'logp0':logs['0'],'logp1':logs['1'],'p0':a,'p1':b,'binary_mass':a+b,
                    'log_odds':logs['1']-logs['0'],'p1_conditional':q,'p_to_do':semantic}
        for key,x in calculated.items():
            e=abs(x-r['result'][key]);maxerr=max(maxerr,e);assert e<1e-12
        if r['item']['kind']=='canary':
            qcdiffs.append(abs(r['result']['p1_conditional']-r['item']['expected']['p1_conditional']))
            rawdiffs.extend(abs(logs[k]-r['item']['expected']['logp'+k]) for k in ['0','1'])
        else:
            masses.append(a+b)
            if r['item']['kind']=='primary':
                c,s,k=r['item']['pair'];values[k,cs.index(c),ids.index(s)]=semantic
    assert np.isfinite(values).all() and ((values>=0)&(values<=1)).all()
    for k,(name,_,_) in enumerate(CONDITIONS):
        _,_,exported=read(out/f'probabilities-{name}.csv');assert np.max(abs(values[k]-exported))<1e-12
    _,_,exported=read(out/'probabilities-counterbalanced.csv');assert np.max(abs(values.mean(0)-exported))<1e-12
    db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute("SELECT COUNT(*) FROM evaluations WHERE state='inflight'").fetchone()[0]
        all_attempts=[dict(a) for a in db.execute('SELECT * FROM attempts')]
        counts=Counter();costs=defaultdict(float);adaptive=0
        for row in db.execute("SELECT record FROM evaluations WHERE state='valid'"):
            r=json.loads(row['record']);k=r['item']['kind'];counts[k]+=1;costs[k]+=r['response']['usage']['cost']
            adaptive+=int(k=='canary' and '-resume' in r['item']['pair'][1])
    finally:db.close()
    assert not any(a['state']=='reserved' for a in all_attempts)
    remaining={'primary':m['counts']['primary']-counts['primary'],'baseline':m['counts']['baseline']-counts['baseline'],
               'canary':m['counts']['scheduled_canaries']-(counts['canary']-adaptive)}
    charged=sum(a['charged'] for a in all_attempts)/1e9;known=sum(a['charged'] for a in all_attempts if a['actual_cost'] is not None)/1e9
    assert charged<=10
    estimate=sum(remaining[k]*costs[k]/counts[k] for k in remaining)*(1+max(0,charged-sum(costs.values()))/sum(costs.values()))
    invocations={}
    for b in range(1,batch+1):
        for p in (root/f'batch-{b:04d}').glob('execution-*.json'):
            x=json.loads(p.read_text());key=(b,x['started_at'])
            if key not in invocations or x['elapsed_seconds_this_invocation']>invocations[key]['elapsed_seconds_this_invocation']:invocations[key]=x
    elapsed=sum(x['elapsed_seconds_this_invocation'] for x in invocations.values());rate=sum(x['new_valid_this_invocation'] for x in invocations.values())/elapsed
    report.update(remaining=remaining,estimated_remaining_cost_usd_at_observed_token_usage=estimate,
                  estimated_total_cost_usd=charged+estimate,estimated_remaining_inference_seconds_at_observed_rate=sum(remaining.values())/rate,
                  projection_basis='Cumulative usage and conservative failed-attempt charges; scheduled canaries exclude separately counted resume canaries.',
                  later_batch_authorized=batch!=group[-1],next_batch_in_authorized_group=batch+1 if batch!=group[-1] else None,
                  group_authorization_path=str(scope_path),
                  first_unauthorized_batch=prohibited,no_later_group_authorization=True,scheduled_canaries=30,adaptive_resume_canaries=0,
                  aggregate_active_dispatch_seconds=elapsed,aggregate_valid_evaluations_per_second=rate,
                  cumulative_confirmed_spending_usd=known,cumulative_conservative_spending_usd=charged,
                  binary_mass_quantiles=dict(zip(['min','q25','median','q75','max'],map(float,np.quantile(masses,[0,.25,.5,.75,1])))),
                  binary_mass_below_0_9=sum(x<.9 for x in masses),maximum_independent_probability_error=maxerr,
                  prompt_tokens_reported_by_responses=report.pop('prompt_tokens_all_attempts'),
                  completion_tokens_reported_by_responses=report.pop('completion_tokens_all_attempts'),
                  all_attempt_billing_usage_known=report['unknown_billing_attempts']==0)
    (out/'batch-report.json').write_text(json.dumps(report,indent=2)+'\n')
    result.update(all_required_token_logs_available=True,all_label_tokens_literal_ASCII=True,
                  maximum_independent_probability_error=maxerr,canary_max_probability_difference=max(qcdiffs),
                  canary_max_raw_logprob_difference=max(rawdiffs),all_four_semantic_probability_matrices_recomputed=True,
                  counterbalanced_matrix_recomputed=True,prior_records_postcheck_passed=True)
    (out/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    backup=Path('/workspace/backups/granite-exploratory')/rid;ledger=backup/(stage+'-ledger.sqlite')
    from granite_backup import resolve_snapshot
    recovery=resolve_snapshot(ledger)
    assert recovery['all_tables']['attempts']['rows']==len(all_attempts)
    suffix='reactivated' if group==[4,5] else f'group-{group[0]:04d}-{group[-1]:04d}'
    archive=backup/(stage+'-'+suffix+'-raw-curated-evidence.tar.gz');assert not archive.exists()
    with tarfile.open(archive,'w:gz') as t:
        t.add(root/stage,arcname='operational/'+stage);t.add(out,arcname='curated/'+stage)
        t.add(root/'manifest.json',arcname='manifest.json')
        t.add(scope_path,arcname='group-authorization.json')
    frozen_json(out/'preservation-manifest.json',{'run_id':rid,'stage':stage,'completed_ledger_backup':{'path':str(ledger),'sha256':recovery['source_sha256'],'recovery_metadata':str(ledger)+'.recovery.json','archive_path':recovery['archive_path'],'archive_sha256':recovery['archive_sha256']},
        'raw_evidence_archive':{'path':str(archive),'sha256':file_hash(archive)},'curated_files_sha256':{str(p):file_hash(p) for p in sorted(out.rglob('*')) if p.is_file()},
        'authoritative_ledger_committed':False,'historical_authorizations_and_evidence_unchanged':True})
    return {'verification':result,'accounting':report}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);p.add_argument('--scope');a=p.parse_args();print(json.dumps(finish(a.batch,a.scope),indent=2))
