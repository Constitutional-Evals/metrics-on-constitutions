"""Cumulative read-only ledger report; never authorizes or dispatches a batch."""
import argparse
from collections import Counter,defaultdict
import fcntl
import json
from pathlib import Path
import sqlite3

from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE,CANARY,frozen_json,verify_manifest


def report(through, recovery_scope=None):
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m)
    rid=digest(m);root=Path('/workspace/work/granite-exploratory')/rid
    with (root/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:
            stages=[dict(r) for r in db.execute('SELECT * FROM dispatch_stages ORDER BY id')]
            assert [r['id'] for r in stages]==[f'batch-{j:04d}' for j in range(1,through+1)],'Unexpected stage history'
            attempts=[dict(r) for r in db.execute('SELECT * FROM attempts ORDER BY started,id')]
            cap=db.execute('SELECT cap FROM settings').fetchone()[0];assert cap==10_000_000_000
            records=(json.loads(r['record']) for r in db.execute("SELECT record FROM evaluations WHERE run=? AND state='valid'",(rid,)))
            counts=Counter();costs=defaultdict(float);models=Counter();providers=Counter();qcdiffs=[];adaptive_qc=0
            for r in records:
                k=r['item']['kind'];counts[k]+=1;costs[k]+=r['response']['usage']['cost']
                models[r['response']['model']]+=1;providers[r['response']['provider']]+=1
                if k=='canary':
                    qcdiffs.append(abs(r['result']['p1_conditional']-r['item']['expected']['p1_conditional']))
                    adaptive_qc+=int('-resume' in r['item']['pair'][1])
            complete_scenarios=db.execute("SELECT COUNT(*) FROM (SELECT sid FROM evaluations WHERE run=? AND cid!=? AND state='valid' GROUP BY sid HAVING COUNT(*)=100)",(rid,CANARY)).fetchone()[0]
            logical_states=dict(db.execute('SELECT state,COUNT(*) FROM evaluations WHERE run=? GROUP BY state',(rid,)))
        finally:db.close()
    summaries=[json.loads((root/r['id']/'summary.json').read_text()) for r in stages]
    # Chunk snapshots are cumulative within one invocation, so count only its latest snapshot.
    invocations={}
    for stage in stages:
        for p in (root/stage['id']).glob('execution-*.json'):
            x=json.loads(p.read_text());key=(stage['id'],x['started_at'])
            if key not in invocations or x['elapsed_seconds_this_invocation']>invocations[key]['elapsed_seconds_this_invocation']:invocations[key]=x
    elapsed=sum(v['elapsed_seconds_this_invocation'] for v in invocations.values())
    completed_this_history=sum(v['new_valid_this_invocation'] for v in invocations.values())
    rate=completed_this_history/elapsed
    charged=sum(a['charged'] for a in attempts)/1e9;actual=sum(a['charged'] for a in attempts if a['actual_cost'] is not None)/1e9
    held=sum(a['reserve'] for a in attempts if a['state']=='reserved')/1e9
    remaining={k:max(0,m['counts'][k if k!='canary' else 'scheduled_canaries']-counts[k]) for k in ['primary','baseline','canary']}
    remaining['canary']=max(0,m['counts']['scheduled_canaries']-(counts['canary']-adaptive_qc))
    validcost=sum(costs.values());failurecharges=max(0,charged-validcost)
    inflation=1+failurecharges/validcost if validcost else 1
    estimate=sum(remaining[k]*costs[k]/counts[k] for k in remaining)*inflation
    latest=through;next_batch=through+1
    blocked=False
    if recovery_scope is not None:
        scope=json.loads(Path(recovery_scope).read_text())
        assert scope['run_id']==rid and scope['approved_execution_batches']==[through]
        assert [through+1,through+2]==scope['do_not_execute_batches'] and scope['all_later_batches_blocked']
        blocked=True
    conditional_file=Path(f'configs/granite-exploratory-authorizations/batch-{next_batch:04d}.json').exists()
    result={'run_id':rid,'through_batch':through,'status':'PAUSED_AFTER_RECOVERY_BATCH_ONLY' if blocked else 'PAUSED_AFTER_AUTHORIZED_BATCH',
      'valid':dict(counts),'total_valid':sum(counts.values()),'complete_scenarios':complete_scenarios,
      'valid_scheduled_canaries':counts['canary']-adaptive_qc,'valid_adaptive_resume_canaries':adaptive_qc,
      'physical_attempts':len(attempts),'failed_attempts':sum(a['state'] not in ['valid','reserved'] for a in attempts),
      'failed_attempt_reasons':dict(Counter(a['error'] for a in attempts if a['error'])),
      'http_status_counts':dict(Counter(str(a['http_status']) for a in attempts)),
      'actual_spending_usd':actual,'conservative_spending_usd':charged,'global_cap_usd':cap/1e9,
      'unspent_global_budget_usd':cap/1e9-charged-held,'outstanding_reservations_usd':held,
      'unknown_billing_attempts':sum(a['actual_cost'] is None for a in attempts),
      'logical_state_counts':logical_states,'remaining':remaining,'remaining_scheduled_evaluations':sum(remaining.values()),
      'completed_batches':sum(s['status']=='COMPLETE' for s in summaries),'remaining_batches':len(m['batches'])-through,
      'aggregate_active_dispatch_seconds':elapsed,'aggregate_valid_evaluations_per_second':rate,
      'estimated_remaining_cost_usd':estimate,'estimated_final_cost_usd':charged+estimate,
      'estimated_remaining_active_inference_seconds':sum(remaining.values())/rate,
      'projection_limitations':'Approx±20% variation; task setup/approval delays, throttling, price changes and extra resume QC can add time/cost.',
      'maximum_canary_probability_difference':max(qcdiffs,default=None),'model_counts':dict(models),'provider_counts':dict(providers),
      'registered_stages':[s['id'] for s in stages],'next_batch':next_batch,
      'next_batch_authorized':conditional_file and not blocked,
      'next_batch_conditional_authorization_file_present':conditional_file,
      'later_batches_blocked_by_latest_recovery_scope':blocked,
      'interpretation':'Granite-conditioned exploratory behavior under24prompts; batch outputs are not full-library philosophical distances.'}
    assert not result['next_batch_authorized'],'Later batch authorization unexpectedly exists'
    out=Path('results/granite-exploratory');frozen_json(out/f'progress-after-batch-{through:04d}.json',result)
    boundary=(f'Execution is stopped after Batch {through}. Batches {next_batch} and {next_batch+1} remain blocked by the latest recovery-only instruction, despite historical conditional authorization files. No later batch was launched.'
              if blocked else f'Execution is stopped. Batch {next_batch} and later batches have not been authorized or launched.')
    text=f'''# Cumulative Granite exploratory progress through Batch {through}

**{boundary}**
This is the current cumulative report; earlier reports remain historical snapshots.

Frozen run: `{rid}`. The original experiment-wide ledger, immutable protocol from
commit a8c1a66, $10 cap, and all historical spending are retained.

| Completed component | Valid evaluations |
|---|---:|
| Primary | {counts['primary']:,} |
| No-constitution baseline | {counts['baseline']:,} |
| Canaries | {counts['canary']:,} |
| Total | {sum(counts.values()):,} |

All {complete_scenarios} completed scenarios have all 24 constitutions, four
conditions, and four baseline responses. There are {len(attempts):,} physical
attempts, including {result['failed_attempts']} failed attempts preserved in the
ledger. Confirmed response charges are **${actual:.9f}**; conservative spending
accounted against the $10 cap is **${charged:.9f}**, including full charges for
{result['unknown_billing_attempts']} uncertain billing outcomes. Outstanding
reservations are ${held:.9f}. Exact total billing is not yet known. All valid responses report the requested
Granite model and Cloudflare. Maximum canary conditional-probability deviation
is {result['maximum_canary_probability_difference']}.

Remaining: **{remaining['primary']:,} primary**, **{remaining['baseline']:,}
baselines**, and **{remaining['canary']:,} scheduled canaries**, across
**{len(m['batches'])-through} batches**. At the aggregate observed rate of
{rate:.3f} valid evaluations/second, expected remaining active inference is
**{result['estimated_remaining_active_inference_seconds']/3600:.2f} hours**.
Estimated remaining cost is **${estimate:.2f}**, or **${charged+estimate:.2f} total**.
Allow roughly ±20% variation plus setup, throttling and approval delays; these
estimates do not authorize further dispatch.

Batch {through} artifacts: [`batch-{through:04d}/batch-report.json`](batch-{through:04d}/batch-report.json),
[`batch-{through:04d}/analysis-summary.json`](batch-{through:04d}/analysis-summary.json),
and its probability matrices, A/B/C normalized and summed-L1 matrices, baseline,
rankings, contributions, subsampling diagnostics and raw evidence. These are
batch-specific results, not the final 1,336-scenario matrices. Distances describe
Granite-conditioned behavior, not verified philosophical distances.

The original 0.125 log-odds quantization limitation and approved automated-screening
scenario-selection policy remain unchanged. Before/after row fingerprints audit
the preservation of prior checkpoints and spending. Verified SQLite and raw
evidence backups are kept outside Git on the same working volume. They are not
off-volume disaster recovery. GitHub holds curated evidence, not the authoritative
ledger. See the backup/export documentation for exact recovery and capacity gates;
credentials and the authoritative ledger are not committed.
'''
    (out/'PROGRESS.md').write_text(text)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--through-batch',type=int,required=True);p.add_argument('--recovery-scope');a=p.parse_args()
    print(json.dumps(report(a.through_batch,a.recovery_scope),indent=2))
