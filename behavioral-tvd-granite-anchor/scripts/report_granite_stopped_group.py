"""Offline stopped-group audit, partial exports, accounting and backups.

Specifically records the stop in authorized group 3–5. Never changes a ledger
row, retries a request, or treats an incomplete batch as a completed matrix.
"""
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import sqlite3
import tarfile

import numpy as np
from analyze_granite_exploratory import matrix, table
from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE, CONDITIONS, frozen_json, verify_manifest
from constitution_distance.local import file_hash
from final_granite_pilot import validate


def report():
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m)
    rid=digest(m);root=Path('/workspace/work/granite-exploratory')/rid
    out=Path('results/granite-exploratory/batch-0003')
    summary=json.loads((out/'summary.json').read_text())
    assert summary['status']=='STOPPED' and summary['missing']==513
    assert json.loads((out/'prior-records-postcheck.json').read_text())['status']=='PASS'
    cs=m['constitution_order'];ids=m['batches'][2]['scenario_ids'];si={s:j for j,s in enumerate(ids)}
    p=np.full((4,24,20),np.nan);base=np.full((4,20),np.nan);seen=set();maxerr=0.
    records=list(map(json.loads,gzip.open(out/'responses.jsonl.gz','rt')))
    for r in records:
        pair=tuple(r['item']['pair']);assert pair not in seen;seen.add(pair)
        assert r['result']==validate(r['item'],r['response'])
        assert r['request_hash']==digest(r['request']) and r['prompt_hash']==digest(r['request']['messages'])
        assert r['response']['model']==m['settings']['model'] and r['response']['provider']=='Cloudflare'
        tokens=r['response']['choices'][0]['logprobs']['content'][0]['top_logprobs']
        logs={t['token']:t['logprob'] for t in tokens if t['token'] in ['0','1']}
        assert set(logs)=={'0','1'}
        assert all(t['bytes']==[ord(t['token'])] for t in tokens if t['token'] in logs)
        a,b=math.exp(logs['0']),math.exp(logs['1']);conditional=b/(a+b)
        semantic=1-conditional if r['item'].get('swapped',False) else conditional
        expected={'logp0':logs['0'],'logp1':logs['1'],'log_odds':logs['1']-logs['0'],
                  'p0':a,'p1':b,'binary_mass':a+b,'p1_conditional':conditional,'p_to_do':semantic}
        for key,x in expected.items():
            err=abs(x-r['result'][key]);maxerr=max(maxerr,err);assert err<1e-12
        if r['item']['kind']=='canary':continue
        c,s,k=pair
        if c==BASELINE:base[k,si[s]]=semantic
        else:p[k,cs.index(c),si[s]]=semantic
    plan={tuple(x['pair']):x for x in map(json.loads,gzip.open('data/granite-exploratory/task-plan.jsonl.gz','rt')) if x['batch']==3}
    for r in records:
        assert r['request_hash']==plan[tuple(r['item']['pair'])]['request_hash']
        assert r['prompt_hash']==plan[tuple(r['item']['pair'])]['prompt_hash']
    def blank(values):return [[None if not math.isfinite(float(x)) else x for x in row] for row in values]
    q=p.mean(0)
    for k,(name,_,_) in enumerate(CONDITIONS):matrix(out/f'probabilities-{name}-INCOMPLETE.csv',blank(p[k]),cs,ids)
    matrix(out/'probabilities-counterbalanced-INCOMPLETE.csv',blank(q),cs,ids)
    table(out/'baseline-INCOMPLETE.csv',[{'scenario':s,**{CONDITIONS[k][0]:float(base[k,j]) if math.isfinite(base[k,j]) else None for k in range(4)},'counterbalanced':float(base[:,j].mean()) if np.isfinite(base[:,j]).all() else None} for j,s in enumerate(ids)])
    complete=np.isfinite(p).all(axis=(0,1)) & np.isfinite(base).all(0)
    selected=[s for s,x in zip(ids,complete) if x];n=len(selected);assert n==14
    subset=out/'complete-case-14-scenarios-NOT-BATCH-RESULT';subset.mkdir(exist_ok=True)
    v=p[:,:,complete];w=v.mean(0)
    sums={'A_primary':abs(w[:,None,:]-w[None,:,:]).sum(-1),
          'B_secondary':abs(v[:,:,None,:]-v[:,None,:,:]).sum(-1).mean(0),
          'C_canonical':abs(v[0,:,None,:]-v[0,None,:,:]).sum(-1)}
    distance_error=0.
    for name,d in sums.items():
        assert np.array_equal(d,d.T) and np.all(d.diagonal()==0) and np.min(d)>=0
        for i in range(24):
            for j in range(24):
                if name=='A_primary':ref=math.fsum(abs(math.fsum(v[k,i,s] for k in range(4))/4-math.fsum(v[k,j,s] for k in range(4))/4) for s in range(n))
                elif name=='B_secondary':ref=math.fsum(abs(v[k,i,s]-v[k,j,s]) for k in range(4) for s in range(n))/4
                else:ref=math.fsum(abs(v[0,i,s]-v[0,j,s]) for s in range(n))
                distance_error=max(distance_error,abs(ref-d[i,j]));assert abs(ref-d[i,j])<1e-12
        matrix(subset/f'distances-{name}-normalized-l1.csv',d/n,cs,cs)
        matrix(subset/f'distances-{name}-summed-l1.csv',d,cs,cs)
    assert np.all(sums['A_primary']<=sums['B_secondary']+1e-12)
    matrix(subset/'probabilities-counterbalanced.csv',w,cs,selected)
    tri=np.triu_indices(24,1)
    diagnostics={'scope':'STOPPED_BATCH_3_INCOMPLETE_20_SCENARIO_GRID','valid_records':len(records),
                 'all_valid_request_hashes_match_frozen_plan':True,'all_valid_responses_have_required_token_logs':True,
                 'maximum_independent_probability_transformation_error':maxerr,
                 'counterbalanced_missing_cells':int(np.isnan(q).sum()),'no_imputation':True,
                 'full_20_scenario_A_B_C_matrices':'NOT_ESTIMABLE; no full-batch distance matrices exported',
                 'complete_case_subset_scenario_ids':selected,'complete_case_subset_count':n,
                 'subset_distance_scope':'Descriptive complete-case 14-scenario subset only; not Batch 3 or 1336-scenario experiment results. Exclusion depends on execution success, not an approved replacement scenario policy.',
                 'maximum_independent_subset_A_B_C_error':distance_error,
                 'subset_mean_normalized_distances':{name:float(d[tri].mean()/n) for name,d in sums.items()},
                 'interpretation':'Granite-conditioned behavior, not established philosophical distances.'}
    (out/'partial-analysis-summary.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert [r[0] for r in db.execute('SELECT id FROM dispatch_stages ORDER BY id')]==['batch-0001','batch-0002','batch-0003']
        assert db.execute('SELECT cap FROM settings').fetchone()[0]==10_000_000_000
        assert db.execute("SELECT COUNT(*) FROM attempts WHERE state='reserved'").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM evaluations WHERE state='inflight'").fetchone()[0]==0
        attempts=[dict(r) for r in db.execute('SELECT * FROM attempts')]
        counts=Counter();costs=defaultdict(float);adaptive=0;canaries=[];models=Counter();providers=Counter()
        for row in db.execute("SELECT record FROM evaluations WHERE state='valid'"):
            r=json.loads(row['record']);kind=r['item']['kind'];counts[kind]+=1;costs[kind]+=r['response']['usage']['cost']
            models[r['response']['model']]+=1;providers[r['response']['provider']]+=1
            if kind=='canary':canaries.append(r);adaptive+=int('-resume' in r['item']['pair'][1])
        logical=dict(db.execute('SELECT state,COUNT(*) FROM evaluations GROUP BY state'))
        complete_scenarios=db.execute("SELECT COUNT(*) FROM (SELECT sid FROM evaluations WHERE cid!='__canary__' AND state='valid' GROUP BY sid HAVING COUNT(*)=100)").fetchone()[0]
    finally:db.close()
    remaining={'primary':m['counts']['primary']-counts['primary'],'baseline':m['counts']['baseline']-counts['baseline'],
               'canary':m['counts']['scheduled_canaries']-(counts['canary']-adaptive)}
    charged=sum(a['charged'] for a in attempts)/1e9;known=sum(a['charged'] for a in attempts if a['actual_cost'] is not None)/1e9
    estimate=sum(remaining[k]*costs[k]/counts[k] for k in remaining)*(1+max(0,charged-sum(costs.values()))/sum(costs.values()))
    invocations={}
    for b in [1,2,3]:
        for path in (root/f'batch-{b:04d}').glob('execution-*.json'):
            x=json.loads(path.read_text());key=(b,x['started_at'])
            if key not in invocations or x['elapsed_seconds_this_invocation']>invocations[key]['elapsed_seconds_this_invocation']:invocations[key]=x
    elapsed=sum(x['elapsed_seconds_this_invocation'] for x in invocations.values())
    rate=sum(x['new_valid_this_invocation'] for x in invocations.values())/elapsed
    failed=[a for a in attempts if a['error'] and a['state']=='invalid'];assert len(failed)==1
    failure=failed[0];envelope=json.loads(failure['response']);assert envelope['error']['code']==504
    result={'run_id':rid,'status':'GROUP_STOPPED_REVIEW_REQUIRED','authorized_group':[3,4,5],
            'completed_batches':[1,2],'stopped_batch':3,'authorized_but_not_started_batches':[4,5],
            'no_batch_6_authorization':not Path('configs/granite-exploratory-authorizations/batch-0006.json').exists(),
            'valid':dict(counts),'total_valid':sum(counts.values()),'complete_scenarios':complete_scenarios,
            'scheduled_canaries':counts['canary']-adaptive,'adaptive_canaries':adaptive,
            'physical_attempts':len(attempts),'failed_attempts':sum(a['state']!='valid' for a in attempts),
            'unknown_billing_attempts':sum(a['actual_cost'] is None for a in attempts),
            'confirmed_spending_usd':known,'conservative_spending_usd':charged,'global_cap_usd':10,
            'outstanding_reservations_usd':0,'remaining_budget_usd':10-charged,
            'unknown_billing_conservative_charges_usd':charged-known,
            'remaining':remaining,'remaining_scheduled_evaluations':sum(remaining.values()),
            'remaining_unfinished_batches':65,'unstarted_batches':64,'logical_state_counts':logical,
            'aggregate_active_dispatch_seconds':elapsed,'aggregate_valid_evaluations_per_second':rate,
            'estimated_remaining_cost_usd':estimate,'estimated_total_cost_usd':charged+estimate,
            'estimated_remaining_active_inference_seconds':sum(remaining.values())/rate,
            'estimated_total_active_inference_seconds':elapsed+sum(remaining.values())/rate,
            'projection_limitations':'Approximate ±20% observed token/throughput variation, excludes setup/review downtime and added resume canaries. Error incidence and backend latency may change.',
            'maximum_canary_probability_deviation':max(abs(r['result']['p1_conditional']-r['item']['expected']['p1_conditional']) for r in canaries),
            'maximum_canary_raw_logprob_deviation':max(abs(r['result'][k]-r['item']['expected'][k]) for r in canaries for k in ['logp0','logp1']),
            'valid_model_counts':dict(models),'valid_provider_counts':dict(providers),
            'batch_3':summary,'failed_task':{k:failure[k] for k in ['id','cid','sid','replica','state','error','http_status','charged','actual_cost']},
            'failure_interpretation':{'envelope_error':envelope['error'],'model_present':False,'provider_present':False,
                'actual_model_provider_drift_established':False,'retry_performed':False,
                'reason_no_auto_retry':'Frozen validator classified HTTP200 error envelope as identity failure; invalid checkpoint requires explicit review before ordinary resume. Group stop policy applied; frozen code and state unchanged.'},
            'prior_records_unchanged':True,'api_requests_for_reporting':0}
    assert result['valid']=={'baseline':220,'canary':84,'primary':5279}
    assert charged==0.283413186 and known==0.27361389
    assert complete_scenarios==54 and result['no_batch_6_authorization']
    frozen_json(Path('results/granite-exploratory/group-0003-0005-stop.json'),result)
    frozen_json(root/'group-0003-0005-stop.json',result)
    batch_report=json.loads((out/'batch-report.json').read_text())
    batch_report.update(remaining=remaining,remaining_batches=65,
                        estimated_remaining_cost_usd_at_observed_token_usage=estimate,estimated_total_cost_usd=charged+estimate,
                        estimated_remaining_inference_seconds_at_observed_rate=sum(remaining.values())/rate,
                        later_batch_authorized=True,later_authorized_batches_blocked_by_group_stop=[4,5],
                        manual_review_required_before_resume=True,failed_envelope_error_code=504,
                        usage_complete_for_all_attempts=False,
                        prompt_tokens_reported_by_responses=batch_report.pop('prompt_tokens_all_attempts'),
                        completion_tokens_reported_by_responses=batch_report.pop('completion_tokens_all_attempts'),
                        accounting_note='Failed response has no usage/cost; full $0.002449824 reservation charged. Confirmed charges are not final billing totals.')
    (out/'batch-report.json').write_text(json.dumps(batch_report,indent=2)+'\n')
    backup=Path('/workspace/backups/granite-exploratory')/rid
    ledger=backup/'batch-0003-ledger.sqlite';assert ledger.exists()
    c=sqlite3.connect(f'file:{ledger}?mode=ro',uri=True)
    try:
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert c.execute('SELECT SUM(charged) FROM attempts').fetchone()[0]==round(charged*1e9)
    finally:c.close()
    archive=backup/'batch-0003-stopped-raw-evidence.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as t:
        t.add(root/'batch-0003',arcname='operational/batch-0003')
        t.add(root/'manifest.json',arcname='manifest.json')
        t.add(out,arcname='curated/batch-0003')
        t.add(root/'group-0003-0005-stop.json',arcname='group-stop.json')
    frozen_json(out/'preservation-manifest.json',{'ledger_backup_path':str(ledger),'ledger_backup_sha256':file_hash(ledger),
                'raw_evidence_backup_path':str(archive),'raw_evidence_backup_sha256':file_hash(archive),
                'curated_files_sha256':{str(p):file_hash(p) for p in sorted(out.rglob('*')) if p.is_file()},
                'authoritative_ledger_committed':False})
    return result


if __name__=='__main__':print(json.dumps(report(),indent=2))
