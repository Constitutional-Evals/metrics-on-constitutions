"""Offline completed recovery export; retain all stopped evidence and backups."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3

from constitution_distance.core import digest
from constitution_distance.exploratory import frozen_json,verify_manifest
from constitution_distance.local import file_hash
from preserve_granite_exploratory import packed


def preserve():
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());verify_manifest(m)
    rid=digest(m);root=Path('/workspace/work/granite-exploratory')/rid;src=root/'batch-0003'
    out=Path('results/granite-exploratory/batch-0003')
    s=json.loads((src/'summary.json').read_text());assert s['status']=='COMPLETE' and s['missing']==0
    assert s['valid']=={'primary':1920,'baseline':80,'canary':36}
    attempts=json.loads((src/'attempts.json').read_text());records=[json.loads(x) for x in (src/'responses.jsonl').read_text().splitlines()]
    for name in ['summary.json','missing.json','authorization.json']:shutil.copyfile(src/name,out/name)
    for name in ['responses.jsonl','attempts.json']:packed(src/name,out/(name+'.gz'))
    for p in src.glob('execution-*.json'):shutil.copyfile(p,out/p.name)
    for p in root.glob('endpoint-*.json'):shutil.copyfile(p,out/p.name)
    invocations={}
    for p in src.glob('execution-*.json'):
        x=json.loads(p.read_text());key=x['started_at']
        if key not in invocations or x['elapsed_seconds_this_invocation']>invocations[key]['elapsed_seconds_this_invocation']:invocations[key]=x
    elapsed=sum(x['elapsed_seconds_this_invocation'] for x in invocations.values())
    progress=json.loads(Path('results/granite-exploratory/progress-after-batch-0003.json').read_text())
    costs=[r['response']['usage']['cost'] for r in records];qc=[r for r in records if r['item']['kind']=='canary']
    latencies=[(datetime.fromisoformat(a['finished'])-datetime.fromisoformat(a['started'])).total_seconds() for a in attempts if a['finished']]
    r={'run_id':rid,'stage':'batch-0003','status':'COMPLETE','valid':s['valid'],'physical_attempts':len(attempts),
       'failed_attempts':s['failed_attempts'],'unknown_billing_attempts':sum(a['actual_cost'] is None for a in attempts),
       'http_status_counts':dict(Counter(str(a['http_status']) for a in attempts)),
       'failure_reasons':dict(Counter(a['error'] for a in attempts if a['error'])),
       'unresolved_evaluations':0,'primary_physical_attempts':s['primary_physical_attempts'],
       'stage_budget':s['stage_budget'],'experiment_budget':s['experiment_budget'],'cost_of_valid_records_usd':sum(costs),
       'remaining':progress['remaining'],'remaining_batches':progress['remaining_batches'],
       'elapsed_seconds':s['elapsed_seconds_this_invocation'],'elapsed_seconds_all_invocations':elapsed,
       'valid_evaluations_per_second':len(records)/elapsed,'primary_evaluations_per_second':1920/elapsed,
       'mean_attempt_latency_seconds':sum(latencies)/len(latencies),
       'estimated_remaining_inference_seconds_at_observed_rate':progress['estimated_remaining_active_inference_seconds'],
       'estimated_remaining_cost_usd_at_observed_token_usage':progress['estimated_remaining_cost_usd'],
       'estimated_total_cost_usd':progress['estimated_final_cost_usd'],'projection_limitations':progress['projection_limitations'],
       'canary_max_conditional_probability_difference':max(abs(x['result']['p1_conditional']-x['item']['expected']['p1_conditional']) for x in qc),
       'canary_max_raw_logprob_difference':max(abs(x['result'][k]-x['item']['expected'][k]) for x in qc for k in ['logp0','logp1']),
       'canary_max_log_odds_difference':max(abs(x['result']['log_odds']-x['item']['expected']['log_odds']) for x in qc),
       'model_counts':dict(Counter(x['response']['model'] for x in records)),
       'provider_counts':dict(Counter(x['response']['provider'] for x in records)),
       'minimum_binary_mass':min(x['result']['binary_mass'] for x in records),
       'sampled_format_violations':sum(not x['result']['format_compliant'] for x in records),
       'prompt_tokens_all_attempts':sum((json.loads(a['response']) if a['response'] else {}).get('usage',{}).get('prompt_tokens',0) for a in attempts),
       'completion_tokens_all_attempts':sum((json.loads(a['response']) if a['response'] else {}).get('usage',{}).get('completion_tokens',0) for a in attempts),
       'later_batch_authorized':False,'later_conditional_authorization_files_blocked':[4,5],
       'checkpoint':'Original authoritative SQLite; only one reviewed logical-state reclassification; no valid evaluation repeated.'}
    (out/'batch-report.json').write_text(json.dumps(r,indent=2)+'\n')
    backup=Path('/workspace/backups/granite-exploratory')/rid/'batch-0003-completed-reviewed-recovery-ledger.sqlite'
    assert not backup.exists(),'Never overwrite a historical backup'
    c=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True);t=sqlite3.connect(backup)
    try:
        c.backup(t);assert t.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert t.execute('SELECT SUM(charged) FROM attempts').fetchone()==c.execute('SELECT SUM(charged) FROM attempts').fetchone()
    finally:t.close();c.close()
    frozen_json(Path('results/granite-exploratory/batch-0003-recovery/completed-ledger-backup.json'),
                {'path':str(backup),'sha256':file_hash(backup),'sqlite_integrity_check':'ok','historical_backups_overwritten':False})
    return r


if __name__=='__main__':print(json.dumps(preserve(),indent=2))
