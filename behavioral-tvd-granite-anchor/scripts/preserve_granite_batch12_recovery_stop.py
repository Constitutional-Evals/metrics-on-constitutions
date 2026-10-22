"""Offline post-audit and preservation after the reviewed recovery stopped again.

No inference, ledger settlement or checkpoint mutation occurs in this program.
"""
from collections import Counter,defaultdict
import fcntl
import gzip
import json
import math
from pathlib import Path
import shutil
import sqlite3
import tarfile

import numpy as np
from audit_granite_group import snapshot
from analyze_granite_exploratory import matrix,table
from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE,CANARY,CONDITIONS,batch_items,canary_items,resume_canary_items,frozen_json,verify_manifest
from constitution_distance.local import file_hash
from final_granite_pilot import validate
from granite_backup import create_snapshot
from preserve_granite_exploratory import packed
from recover_granite_batch12_timeout import ROOT,OUT,RID,PAIR,AID,connect


def preserve():
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m)
    pre=json.loads((OUT/'preflight.json').read_text());committed=json.loads((OUT/'recovery-committed.json').read_text());assert committed['sql_rows_changed']==1
    src=ROOT/'batch-0012';out=Path('results/granite-exploratory/batch-0012')
    summary=json.loads((src/'summary.json').read_text());assert summary['status']=='STOPPED' and summary['valid']=={'primary':1919,'baseline':80,'canary':30} and summary['missing']==7
    records=list(map(json.loads,(src/'responses.jsonl').read_text().splitlines()));attempts=json.loads((src/'attempts.json').read_text())
    assert len(records)==2029 and len(attempts)==2031
    items=batch_items(m,12)+[i for j in range(5) for i in canary_items(m,12,j)]+resume_canary_items(m,12,1)
    bypair={tuple(i['pair']):i for i in items};lookup={json.dumps(list(p)):i for p,i in bypair.items()}
    maxerr=0.;rawdiff=0.;pdiff=0.;seen=set();p=np.full((4,24,20),np.nan);base=np.full((4,20),np.nan);ids=m['batches'][11]['scenario_ids'];cs=m['constitution_order']
    for r in records:
        pair=tuple(r['item']['pair']);assert pair not in seen;seen.add(pair);i=bypair[pair]
        assert r['request']==i['request'] and r['request_hash']==digest(i['request']) and r['prompt_hash']==digest(i['request']['messages'])
        assert r['result']==validate(i,r['response'])
        assert r['response']['model']==m['settings']['model'] and r['response']['provider']=='Cloudflare'
        tokens=[t for t in r['response']['choices'][0]['logprobs']['content'][0]['top_logprobs'] if t['token'] in ['0','1']]
        assert len(tokens)==2 and all(t['bytes']==[ord(t['token'])] for t in tokens)
        logs={t['token']:t['logprob'] for t in tokens};assert set(logs)=={'0','1'}
        a,b=math.exp(logs['0']),math.exp(logs['1']);cond=b/(a+b);semantic=1-cond if i.get('swapped',False) else cond
        for k,x in {'logp0':logs['0'],'logp1':logs['1'],'p0':a,'p1':b,'binary_mass':a+b,'log_odds':logs['1']-logs['0'],'p1_conditional':cond,'p_to_do':semantic}.items():
            maxerr=max(maxerr,abs(x-r['result'][k]));assert abs(x-r['result'][k])<1e-12
        assert 0<=semantic<=1
        if i['kind']=='canary':
            rawdiff=max(rawdiff,*(abs(r['result'][k]-i['expected'][k]) for k in ['logp0','logp1']))
            pdiff=max(pdiff,abs(r['result']['p1_conditional']-i['expected']['p1_conditional']))
        else:
            c,s,k=pair
            if c==BASELINE:base[k,ids.index(s)]=semantic
            else:p[k,cs.index(c),ids.index(s)]=semantic
    assert np.isnan(p).sum()==1 and np.isfinite(base).all()
    priorids=set(pre['fingerprints']['attempts']);new=[a for a in attempts if a['id'] not in priorids]
    assert len(new)==198 and sum(a['state']=='valid' for a in new)==197
    failed=[a for a in new if a['state']!='valid'];assert len(failed)==1;failure=failed[0]
    assert (failure['cid'],failure['sid'],failure['replica'])==('ubuntu','29912',1) and failure['id']=='429eb30c2dcd4a238d3fa886fdcb7b7e'
    assert failure['state']=='invalid' and failure['http_status']==200 and failure['charged']==failure['reserve']==2449824 and failure['actual_cost'] is None
    response=json.loads(failure['response']);assert response['error']=={'message':'Upstream idle timeout exceeded','code':504,'metadata':{'error_type':'timeout'}}
    assert all(response.get(k) is None for k in ['model','provider','choices','usage'])
    fresh=[a for a in new if a['cid']==CANARY];assert len(fresh)==6 and all(a['state']=='valid' and '-resume0001-' in a['sid'] for a in fresh)
    science=[a for a in new if a['cid']!=CANARY]
    assert min(a['started'] for a in science)>=max(a['finished'] for a in fresh)
    target=[a for a in attempts if (a['cid'],a['sid'],a['replica'])==PAIR];assert len(target)==2
    assert digest(next(a for a in target if a['id']==AID))==pre['original_attempt_sha256']
    retry=next(a for a in target if a['id']!=AID);assert retry['state']=='valid'
    assert retry['request']==next(a for a in target if a['id']==AID)['request']
    with (ROOT/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);db=connect()
        try:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            prior_stages={f'batch-{b:04d}':snapshot(db,ROOT,m,b) for b in range(1,12)};assert prior_stages==pre['prior_stages']
            all_attempts=[dict(a) for a in db.execute('SELECT * FROM attempts')];byaid={a['id']:a for a in all_attempts}
            assert all(digest(byaid[aid])==h for aid,h in pre['fingerprints']['attempts'].items())
            assert all(dict(db.execute('SELECT * FROM attempts WHERE id=?',(a['id'],)).fetchone())==a for a in attempts)
            oldvalid=pre['fingerprints']['valid_evaluations'];other=pre['fingerprints']['all_other_evaluations'];changed=0
            for row in db.execute('SELECT * FROM evaluations'):
                k=json.dumps([row['cid'],row['sid'],row['replica']]);value=digest(dict(row))
                if k in oldvalid:assert value==oldvalid[k]
                if k in other and value!=other[k]:
                    assert k in lookup and k not in oldvalid;changed+=1
            assert changed==191  # 190 previously pending successes + one new invalid.
            assert db.execute("SELECT COUNT(*) FROM evaluations WHERE state='retry'").fetchone()[0]==0
            invalid=list(db.execute("SELECT cid,sid,replica FROM evaluations WHERE state IN ('invalid','error','inflight')"));assert [tuple(x) for x in invalid]==[('ubuntu','29912',1)]
            assert db.execute("SELECT COUNT(*) FROM attempts WHERE state='reserved'").fetchone()[0]==0
            assert db.execute('SELECT cap FROM settings').fetchone()[0]==10000000000
            assert db.execute("SELECT cap,primary_cap FROM dispatch_stages WHERE id='batch-0012'").fetchone()[:]==(1000000000,2000)
            assert [r[0] for r in db.execute('SELECT id FROM dispatch_stages ORDER BY id')]==[f'batch-{b:04d}' for b in range(1,13)]
            assert db.execute('SELECT MAX(n) FROM (SELECT COUNT(*) n FROM attempts GROUP BY run,cid,sid,replica)').fetchone()[0]<=3
            counts=Counter();costs=defaultdict(float);adaptive=0;models=Counter();providers=Counter()
            for row in db.execute("SELECT record FROM evaluations WHERE state='valid'"):
                r=json.loads(row['record']);kind=r['item']['kind'];counts[kind]+=1;costs[kind]+=r['response']['usage']['cost'];models[r['response']['model']]+=1;providers[r['response']['provider']]+=1
                adaptive+=int(kind=='canary' and '-resume' in r['item']['pair'][1])
            complete=db.execute("SELECT COUNT(*) FROM (SELECT sid FROM evaluations WHERE cid!=? AND state='valid' GROUP BY sid HAVING COUNT(*)=100)",(CANARY,)).fetchone()[0]
            assert counts=={'primary':23039,'baseline':960,'canary':372} and adaptive==18 and complete==239
            backup=Path('/workspace/backups/granite-exploratory')/RID
            saved=create_snapshot(db,backup/'batch-0012-reviewed-recovery-stopped-ledger.sqlite')
        finally:db.close()
    proof={'status':'PASS','reviewed_one_row_transition_succeeded':True,'prior_valid_rows_preserved':len(pre['fingerprints']['valid_evaluations']),
      'all_historical_attempts_preserved':len(priorids),'all_other_unauthorized_logical_rows_unchanged':True,'prior_11_batches_unchanged':True,
      'reviewed_request_succeeded_on_lifetime_attempt':2,'new_failed_checkpoint_not_reclassified':True,'fresh_resume_canaries':6,'resume_canaries_finished_before_new_science':True,
      'maximum_independent_probability_error':maxerr,'canary_max_raw_logprob_difference':rawdiff,'canary_max_stored_probability_difference':pdiff,
      'all_valid_requests_and_distributions_verified':True,'one_missing_primary_condition_probability':True,'no_full_batch_or_240_scenario_distances':True,
      'source_hashes_unchanged':True,'api_requests_for_verification':0,'new_backup_exact_restoration_and_all_table_verification':True}
    frozen_json(OUT/'checkpoint-postcheck.json',proof)
    # Preserve the original stop separately; update only the current curated view.
    for name in ['summary.json','missing.json','authorization.json']:shutil.copyfile(src/name,out/name)
    for name in ['responses.jsonl','attempts.json']:packed(src/name,out/(name+'.gz'))
    for pth in src.glob('execution-*.json'):shutil.copyfile(pth,out/pth.name)
    for pth in ROOT.glob('endpoint-*.json'):shutil.copyfile(pth,out/pth.name)
    def blank(v):return [[float(x) if math.isfinite(float(x)) else None for x in row] for row in v]
    for k,(name,_,_) in enumerate(CONDITIONS):matrix(out/f'probabilities-{name}-INCOMPLETE.csv',blank(p[k]),cs,ids)
    matrix(out/'probabilities-counterbalanced-INCOMPLETE.csv',blank(p.mean(0)),cs,ids)
    table(out/'baseline-INCOMPLETE.csv',[{'scenario':sid,**{CONDITIONS[k][0]:float(base[k,j]) for k in range(4)},'counterbalanced':float(base[:,j].mean())} for j,sid in enumerate(ids)])
    inv={}
    for b in range(1,13):
        for path in (ROOT/f'batch-{b:04d}').glob('execution-*.json'):
            x=json.loads(path.read_text());key=(b,x['started_at'])
            if key not in inv or x['elapsed_seconds_this_invocation']>inv[key]['elapsed_seconds_this_invocation']:inv[key]=x
    elapsed=sum(x['elapsed_seconds_this_invocation'] for x in inv.values());rate=sum(x['new_valid_this_invocation'] for x in inv.values())/elapsed
    charged=sum(a['charged'] for a in all_attempts)/1e9;known=sum(a['charged'] for a in all_attempts if a['actual_cost'] is not None)/1e9
    remaining={'primary':128256-counts['primary'],'baseline':5344-counts['baseline'],'canary':2010-(counts['canary']-adaptive)}
    cost=sum(costs.values());estimate=sum(remaining[k]*costs[k]/counts[k] for k in remaining)*(1+max(0,charged-cost)/cost)
    result={'run_id':RID,'status':'REVIEWED_TARGET_RECOVERED_BATCH12_STOPPED_AGAIN','batch12_complete':False,'completed_new_batches':[],
      'recovery_transaction_id':committed['transaction_id'],'logical_rows_changed_in_reviewed_transaction':1,'reviewed_target':{'constitution':PAIR[0],'scenario':PAIR[1],'condition':'canonical','original_failed_attempt_id':AID,'retry_attempt_id':retry['id'],'lifetime_attempt_count':2,'retry_succeeded':True,'original_failed_attempt_and_charge_unchanged':True},
      'new_failure':{'attempt_id':failure['id'],'attempt_sha256':digest(failure),'constitution':'ubuntu','scenario':'29912','condition':'labels_swapped','http_status':200,'response_error':response['error'],'frozen_validator_error':failure['error'],'actual_billing_unknown':True,'full_charge_usd':.002449824,'checkpoint_state':'invalid','reclassified_or_retried':False},
      'recovery_new_physical_attempts':198,'recovery_valid_responses':197,'reviewed_retries':1,'additional_automatic_retries':0,'recovery_new_failures':1,'fresh_resume_canaries':6,
      'stage_valid':summary['valid'],'stage_scheduled_canaries':24,'stage_resume_canaries':6,'stage_missing_scheduled':7,'stage_primary_physical_attempts':summary['primary_physical_attempts'],
      'stage_confirmed_spending_usd':summary['stage_budget']['actual_spending_usd'],'stage_conservative_spending_usd':summary['stage_budget']['conservative_spending_usd'],
      'recovery_confirmed_spending_usd':(sum(a['charged'] for a in new if a['actual_cost'] is not None))/1e9,'recovery_conservative_spending_usd':sum(a['charged'] for a in new)/1e9,
      'recovery_active_seconds':summary['elapsed_seconds_this_invocation'],'recovery_valid_per_second':summary['valid_evaluations_per_second'],
      'stage_active_seconds_all_invocations':sum(x['elapsed_seconds_this_invocation'] for (b,_),x in inv.items() if b==12),
      'valid':dict(counts),'total_valid':sum(counts.values()),'scheduled_canaries':counts['canary']-adaptive,'resume_canaries':adaptive,'fully_observed_scenarios':complete,'completed_batches':11,'last_complete_cumulative_matrix_scenarios':220,
      'physical_attempts':len(all_attempts),'failed_attempts':sum(a['state'] not in ['valid','reserved'] for a in all_attempts),'unknown_billing_attempts':sum(a['actual_cost'] is None for a in all_attempts),
      'confirmed_spending_usd':known,'conservative_spending_usd':charged,'outstanding_reservations_usd':0,'global_cap_usd':10,'stage_cap_usd':1,
      'remaining':remaining,'remaining_scheduled_evaluations':sum(remaining.values()),'unfinished_batches_including12':56,'not_started_batches':55,
      'estimated_remaining_cost_usd':estimate,'estimated_final_cost_usd':charged+estimate,'estimated_remaining_active_seconds':sum(remaining.values())/rate,
      'aggregate_active_seconds':elapsed,'aggregate_valid_per_second':rate,'model_counts_all_valid':dict(models),'provider_counts_all_valid':dict(providers),
      'no_later_batches_dispatched_or_authorized_by_recovery':True,'do_not_execute_batches':[13,14],'all_later_dispatch_blocked':True,
      'backup':saved,'disk_after_verification':shutil.disk_usage('/workspace')._asdict(),'same_volume_backup_not_disaster_recovery':True,
      'scientific_scope':'Granite-conditioned behavioral geometry; no full Batch12/240 matrix or substitute 239-scenario analysis.',
      'error_policy_unchanged':True,'original_stopped_evidence_preserved_under':str(OUT/'stopped-curated')}
    frozen_json(OUT/'recovery-outcome.json',result)
    frozen_json(OUT/'post-recovery-ledger-backup.json',saved)
    frozen_json(Path('configs/granite-exploratory-recoveries/batch-0012-second-stop.json'),{'run_id':RID,'status':'STOPPED_NEW_MANUAL_REVIEW_REQUIRED','reviewed_target_recovered':True,'new_failed_attempt_id':failure['id'],'new_failed_attempt_sha256':digest(failure),'do_not_execute_batches':[13,14],'all_later_batches_blocked':True,'new_checkpoint_reclassification_authorized':False})
    report={'run_id':RID,'stage':'batch-0012','status':summary['status'],'valid':summary['valid'],'unresolved_evaluations':7,'physical_attempts':2031,'failed_attempts':2,'unknown_billing_attempts':2,
      'stage_budget':summary['stage_budget'],'experiment_budget':summary['experiment_budget'],'primary_physical_attempts':1921,
      'scheduled_canaries':24,'resume_canaries':6,'elapsed_seconds_this_recovery':summary['elapsed_seconds_this_invocation'],'elapsed_seconds_all_invocations':result['stage_active_seconds_all_invocations'],
      'recovery_outcome_path':str(OUT/'recovery-outcome.json'),'later_batches_authorized':False,'missing_probabilities_not_imputed':True}
    (out/'batch-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'independent-partial-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
    archive=backup/'batch-0012-second-stop-after-reviewed-recovery-evidence.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as t:
        t.add(src,arcname='operational/batch-0012');t.add(out,arcname='curated/batch-0012');t.add(OUT,arcname='recovery-audit');t.add(ROOT/'manifest.json',arcname='manifest.json')
    preservation={'run_id':RID,'status':'STOPPED_AGAIN_AFTER_ONE_REVIEWED_RECOVERY','backup':saved,'raw_evidence_archive':{'path':str(archive),'sha256':file_hash(archive)},
      'curated_files_sha256':{str(pth):file_hash(pth) for pth in out.rglob('*') if pth.is_file() and pth.name!='preservation-manifest.json'},'old_stopped_evidence_preserved_separately':True,'authoritative_ledger_committed':False}
    (out/'preservation-manifest.json').write_text(json.dumps(preservation,indent=2)+'\n');frozen_json(OUT/'second-stop-preservation.json',preservation)
    return result


if __name__=='__main__':print(json.dumps(preserve(),indent=2))
