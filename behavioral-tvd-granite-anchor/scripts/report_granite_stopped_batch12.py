"""Offline preservation and independent audit of the stopped 12–14 group.

Never dispatches, retries, reclassifies a checkpoint or imputes a probability.
Complete-batch/cumulative distance exports are deliberately not produced.
"""
from collections import Counter,defaultdict
from datetime import datetime
import fcntl
import gzip
import json
import math
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile

import numpy as np
from analyze_granite_exploratory import analyze,matrix,table
from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE,CANARY,CONDITIONS,frozen_json,verify_manifest
from constitution_distance.local import file_hash
from final_granite_pilot import validate
from granite_backup import resolve_snapshot,inventory


def reconcile_curated_report(out, result):
    """Correct only the provisional offline report, never the paid ledger."""
    path=out/'batch-report.json'
    initial=out/'batch-report-initial-preservation.json'
    if not initial.exists():shutil.copyfile(path,initial)
    r=json.loads(initial.read_text())
    r.update(remaining=result['remaining'],remaining_batches=result['unfinished_batches_including_stopped'],
             estimated_remaining_cost_usd_at_observed_token_usage=result['estimated_remaining_cost_usd'],
             estimated_total_cost_usd=result['estimated_final_cost_usd'],
             estimated_remaining_inference_seconds_at_observed_rate=result['estimated_remaining_active_seconds'],
             cumulative_confirmed_spending_usd=result['confirmed_spending_usd'],
             cumulative_conservative_spending_usd=result['conservative_spending_usd'],
             later_batch_authorized=False,later_conditional_authorization_files_blocked=[13,14],
             all_attempt_billing_usage_known=False,
             accounting_note='Reconciled stopped-group report supersedes provisional preservation projections. Scheduled-QC remainder excludes historical resume checks; unfinished batches include stopped Batch12. Original provisional report preserved separately. No ledger changes.',
             prompt_tokens_reported_by_responses=r.pop('prompt_tokens_all_attempts'),
             completion_tokens_reported_by_responses=r.pop('completion_tokens_all_attempts'))
    path.write_text(json.dumps(r,indent=2)+'\n')


def report():
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m);rid=digest(m)
    root=Path('/workspace/work/granite-exploratory')/rid;out=Path('results/granite-exploratory/batch-0012')
    summary=json.loads((out/'summary.json').read_text());assert summary['status']=='STOPPED' and summary['missing']==198
    assert json.loads((out/'prior-records-postcheck.json').read_text())['status']=='PASS'
    cs=m['constitution_order'];ids=m['batches'][11]['scenario_ids'];si={s:j for j,s in enumerate(ids)}
    plan={tuple(i['pair']):i for i in map(json.loads,gzip.open('data/granite-exploratory/task-plan.jsonl.gz','rt')) if i['batch']==12}
    records=list(map(json.loads,gzip.open(out/'responses.jsonl.gz','rt')));attempts=json.load(gzip.open(out/'attempts.json.gz','rt'))
    assert len(records)==1832 and len(attempts)==1833
    seen=set();p=np.full((4,24,20),np.nan);base=np.full((4,20),np.nan);maxerr=0.;qcdiffs=[];rawdiffs=[];masses=[]
    for r in records:
        pair=tuple(r['item']['pair']);assert pair not in seen;seen.add(pair)
        assert r['request_hash']==digest(r['request'])==plan[pair]['request_hash']
        assert r['prompt_hash']==digest(r['request']['messages'])==plan[pair]['prompt_hash']
        assert r['result']==validate(r['item'],r['response'])
        assert r['response']['model']==m['settings']['model'] and r['response']['provider']=='Cloudflare'
        tokens=r['response']['choices'][0]['logprobs']['content'][0]['top_logprobs']
        labels=[t for t in tokens if t['token'] in ['0','1']];assert len(labels)==2
        assert all(t['bytes']==[ord(t['token'])] for t in labels)
        logs={t['token']:t['logprob'] for t in labels};assert set(logs)=={'0','1'}
        a,b=math.exp(logs['0']),math.exp(logs['1']);cond=b/(a+b);semantic=1-cond if r['item'].get('swapped',False) else cond
        for key,x in {'logp0':logs['0'],'logp1':logs['1'],'p0':a,'p1':b,'binary_mass':a+b,'log_odds':logs['1']-logs['0'],'p1_conditional':cond,'p_to_do':semantic}.items():
            maxerr=max(maxerr,abs(x-r['result'][key]));assert abs(x-r['result'][key])<1e-12
        assert 0<=semantic<=1;masses.append(a+b)
        if r['item']['kind']=='canary':
            qcdiffs.append(abs(cond-r['item']['expected']['p1_conditional']))
            rawdiffs.extend(abs(logs[k]-r['item']['expected']['logp'+k]) for k in ['0','1'])
        else:
            c,s,k=pair
            if c==BASELINE:base[k,si[s]]=semantic
            else:p[k,cs.index(c),si[s]]=semantic
    for a in attempts:
        pair=(a['cid'],a['sid'],a['replica']);assert a['run']==rid
        assert digest(json.loads(a['request']))==plan[pair]['request_hash'];assert a['prompt_hash']==plan[pair]['prompt_hash']
    bad=[a for a in attempts if a['state']!='valid'];assert len(bad)==1
    failure=bad[0];assert failure['id']=='9b4128fc0dcb469e817b209db3489378'
    assert failure['state']=='invalid' and failure['actual_cost'] is None and failure['charged']==failure['reserve']==2449824
    assert failure['http_status']==200 and failure['error']=='Model/provider mismatch'
    envelope=json.loads(failure['response']);assert envelope['error']['code']==504
    assert 'choices' not in envelope and 'model' not in envelope and 'provider' not in envelope
    def blank(values):return [[float(x) if math.isfinite(float(x)) else None for x in row] for row in values]
    q=p.mean(0)
    for k,(name,_,_) in enumerate(CONDITIONS):matrix(out/f'probabilities-{name}-INCOMPLETE.csv',blank(p[k]),cs,ids)
    matrix(out/'probabilities-counterbalanced-INCOMPLETE.csv',blank(q),cs,ids)
    table(out/'baseline-INCOMPLETE.csv',[{'scenario':sid,**{CONDITIONS[k][0]:float(base[k,j]) if math.isfinite(base[k,j]) else None for k in range(4)},'counterbalanced':float(base[:,j].mean()) if np.isfinite(base[:,j]).all() else None} for j,sid in enumerate(ids)])
    with (root/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert db.execute('SELECT cap FROM settings').fetchone()[0]==10_000_000_000
            assert db.execute("SELECT COUNT(*) FROM attempts WHERE state='reserved'").fetchone()[0]==0
            assert db.execute("SELECT COUNT(*) FROM evaluations WHERE state='inflight'").fetchone()[0]==0
            assert [r[0] for r in db.execute('SELECT id FROM dispatch_stages ORDER BY id')]==[f'batch-{j:04d}' for j in range(1,13)]
            archived=[dict(r) for r in db.execute('SELECT a.* FROM attempts a JOIN stage_attempts s ON s.aid=a.id WHERE s.stage=? ORDER BY a.started,a.id',('batch-0012',))]
            assert archived==attempts
            for r in records:
                c,s,k=r['item']['pair'];row=db.execute('SELECT state,record FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(rid,c,s,k)).fetchone()
                assert row['state']=='valid' and json.loads(row['record'])==r
            all_attempts=[dict(r) for r in db.execute('SELECT * FROM attempts')];counts=Counter();costs=defaultdict(float);models=Counter();providers=Counter();adaptive=0
            for row in db.execute("SELECT record FROM evaluations WHERE state='valid'"):
                r=json.loads(row['record']);kind=r['item']['kind'];counts[kind]+=1;costs[kind]+=r['response']['usage']['cost']
                models[r['response']['model']]+=1;providers[r['response']['provider']]+=1
                adaptive+=int(kind=='canary' and '-resume' in r['item']['pair'][1])
            states=dict(db.execute('SELECT state,COUNT(*) FROM evaluations GROUP BY state'))
            complete_scenarios=db.execute("SELECT COUNT(*) FROM (SELECT sid FROM evaluations WHERE cid!=? AND state='valid' GROUP BY sid HAVING COUNT(*)=100)",(CANARY,)).fetchone()[0]
            backup=Path('/workspace/backups/granite-exploratory')/rid;recovery=resolve_snapshot(backup/'batch-0012-ledger.sqlite')
            with tempfile.TemporaryDirectory(dir=backup,prefix='stopped-state-check-') as td:
                path=Path(td)/'snapshot.sqlite';target=sqlite3.connect(path);db.backup(target);target.close()
                assert inventory(path)==recovery['all_tables']
        finally:db.close()
    # The ordinary completed-batch exporter must still refuse the incomplete grid.
    with tempfile.TemporaryDirectory(dir='/workspace') as td:
        try:analyze(m,root,Path(td)/'refused',12)
        except ValueError as e:refusal=str(e)
        else:raise AssertionError('Incomplete batch was incorrectly exported as complete')
    remaining={'primary':m['counts']['primary']-counts['primary'],'baseline':m['counts']['baseline']-counts['baseline'],'canary':m['counts']['scheduled_canaries']-(counts['canary']-adaptive)}
    charged=sum(a['charged'] for a in all_attempts)/1e9;known=sum(a['charged'] for a in all_attempts if a['actual_cost'] is not None)/1e9
    validcost=sum(costs.values());estimate=sum(remaining[k]*costs[k]/counts[k] for k in remaining)*(1+max(0,charged-validcost)/validcost)
    invocations={}
    for b in range(1,13):
        for path in (root/f'batch-{b:04d}').glob('execution-*.json'):
            x=json.loads(path.read_text());key=(b,x['started_at'])
            if key not in invocations or x['elapsed_seconds_this_invocation']>invocations[key]['elapsed_seconds_this_invocation']:invocations[key]=x
    elapsed=sum(x['elapsed_seconds_this_invocation'] for x in invocations.values());rate=sum(x['new_valid_this_invocation'] for x in invocations.values())/elapsed
    diagnostics={'scope':'STOPPED_BATCH_12_INCOMPLETE_20_SCENARIO_GRID','valid_records':1832,'science_condition_cells_missing':int(np.isnan(p).sum()),'baseline_condition_cells_missing':int(np.isnan(base).sum()),
      'counterbalanced_cells_missing':int(np.isnan(q).sum()),'maximum_independent_probability_error':maxerr,'all_valid_requests_match_frozen_plan':True,'all_valid_responses_have_genuine_ASCII_logs':True,
      'all_observed_probabilities_in_range':True,'no_imputation':True,'no_full_batch_or_280_scenario_distances_exported':True,
      'complete_export_correctly_refused':refusal,'maximum_canary_probability_difference':max(qcdiffs),'maximum_canary_raw_logprob_difference':max(rawdiffs),'minimum_binary_mass':min(masses),
      'fraction_valid_log_odds_on_0_125_grid_tolerance_1e_5':float(np.mean([abs(r['result']['log_odds']-.125*round(r['result']['log_odds']/.125))<1e-5 for r in records])),
      'prior_completed_batch_records_and_attempts_unchanged':True,'all_attempt_archives_match_authoritative_SQLite':True}
    frozen_json(out/'independent-partial-verification.json',diagnostics)
    result={'run_id':rid,'status':'GROUP_STOPPED_MANUAL_REVIEW_REQUIRED','authorized_group':[12,13,14],'completed_new_batches':[],
      'stopped_batch':12,'authorized_but_not_started_batches':[13,14],'all_later_dispatch_blocked':True,'automatic_retry_or_checkpoint_reclassification_performed':False,
      'failure':{'attempt_id':failure['id'],'constitution':failure['cid'],'scenario':failure['sid'],'condition':CONDITIONS[failure['replica']][0],'http_status':200,'response_error':envelope['error'],
                 'frozen_validator_error':failure['error'],'actual_billing_unknown':True,'charged_reservation_usd':failure['charged']/1e9,'attempt_sha256':digest(failure),
                 'interpretation':'Error-only timeout envelope omitted identity and token logs; this does not demonstrate that a different model was actually served.'},
      'new_valid':summary['valid'],'new_physical_attempts':1833,'new_failed_attempts':1,'new_retries':0,'new_unknown_billing_attempts':1,'missing_batch_evaluations':198,
      'stage_confirmed_spending_usd':summary['stage_budget']['actual_spending_usd'],'stage_conservative_spending_usd':summary['stage_budget']['conservative_spending_usd'],
      'stage_active_seconds':summary['elapsed_seconds_this_invocation'],'stage_valid_per_second':summary['valid_evaluations_per_second'],
      'valid':dict(counts),'total_valid':sum(counts.values()),'physical_attempts':len(all_attempts),'failed_attempts':sum(a['state'] not in ['valid','reserved'] for a in all_attempts),
      'unknown_billing_attempts':sum(a['actual_cost'] is None for a in all_attempts),'confirmed_spending_usd':known,'conservative_spending_usd':charged,'global_cap_usd':10,'outstanding_reservations_usd':0,
      'valid_scheduled_canaries':counts['canary']-adaptive,'valid_resume_canaries':adaptive,'complete_scenarios':complete_scenarios,'completed_batches':11,
      'last_complete_batch_cumulative_matrix_scenarios':220,'logical_states':states,'remaining':remaining,'remaining_scheduled_evaluations':sum(remaining.values()),
      'unfinished_batches_including_stopped':56,'not_started_batches':55,'aggregate_active_seconds':elapsed,'aggregate_valid_per_second':rate,
      'estimated_remaining_cost_usd':estimate,'estimated_final_cost_usd':charged+estimate,'estimated_remaining_active_seconds':sum(remaining.values())/rate,
      'projections_are_not_resume_authorization':True,'model_counts_all_valid':dict(models),'provider_counts_all_valid':dict(providers),
      'backup_exact_restore_and_all_table_comparison_passed':True,'completed_ledger_backup':{'original_path':recovery['original_path'],'source_sha256':recovery['source_sha256'],'archive_path':recovery['archive_path'],'archive_sha256':recovery['archive_sha256'],'recovery_metadata':str(backup/'batch-0012-ledger.sqlite')+'.recovery.json'},
      'disk_after_preservation':shutil.disk_usage('/workspace')._asdict(),'same_volume_backup_not_independent_disaster_recovery':True,
      'last_complete_cumulative_analysis':'results/granite-exploratory/cumulative-through-0011/','interpretation':'Granite-conditioned exploratory behavioral distances; incomplete batch not represented as a complete result.'}
    frozen_json(Path('results/granite-exploratory/progress-stopped-batch-0012.json'),result)
    stop={'run_id':rid,'original_group_authorization':'configs/granite-exploratory-authorizations/groups/batches-0012-0014.json','status':'STOPPED_MANUAL_REVIEW_REQUIRED',
      'stopped_batch':12,'do_not_execute_batches':[13,14],'all_later_batches_blocked':True,'resume_requires_new_explicit_review':True,
      'failed_attempt_id':failure['id'],'failed_attempt_sha256':digest(failure),'no_checkpoint_or_billing_mutation':True}
    frozen_json(Path('configs/granite-exploratory-authorizations/groups/batches-0012-0014-stopped.json'),stop)
    shutil.copyfile(str(backup/'batch-0012-ledger.sqlite')+'.recovery.json',out/'stopped-ledger-recovery.json')
    reconcile_curated_report(out,result)
    archive=backup/'batch-0012-stopped-raw-curated-evidence.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as t:
        t.add(root/'batch-0012',arcname='operational/batch-0012');t.add(out,arcname='curated/batch-0012');t.add(root/'manifest.json',arcname='manifest.json')
        t.add('configs/granite-exploratory-authorizations/groups/batches-0012-0014.json',arcname='group-authorization.json')
        t.add('configs/granite-exploratory-authorizations/groups/batches-0012-0014-stopped.json',arcname='group-stop.json')
    frozen_json(out/'preservation-manifest.json',{'run_id':rid,'status':'STOPPED_INCOMPLETE','completed_ledger_backup':result['completed_ledger_backup'],
      'raw_evidence_archive':{'path':str(archive),'sha256':file_hash(archive)},'curated_files_sha256':{str(p):file_hash(p) for p in sorted(out.rglob('*')) if p.is_file()},
      'authoritative_ledger_committed':False,'no_later_batch_launched':True})
    return result


if __name__=='__main__':print(json.dumps(report(),indent=2))
