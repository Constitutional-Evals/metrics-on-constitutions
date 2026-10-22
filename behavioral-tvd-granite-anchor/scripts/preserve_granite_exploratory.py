"""Curate one completed/stopped stage and independently back up its ledger."""
import argparse
from collections import Counter
from datetime import datetime
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE, CANARY
from constitution_distance.local import file_hash


def packed(source,destination):
    with Path(source).open('rb') as src,Path(destination).open('wb') as dst:
        with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0) as z:shutil.copyfileobj(src,z)


def preserve(batch):
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());rid=digest(m)
    root=Path('/workspace/work/granite-exploratory')/rid;stage=f'batch-{batch:04d}';src=root/stage
    out=Path('results/granite-exploratory')/stage;out.mkdir(parents=True,exist_ok=True)
    with (root/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        summary=json.loads((src/'summary.json').read_text());attempts=json.loads((src/'attempts.json').read_text())
        records=[json.loads(s) for s in (src/'responses.jsonl').read_text().splitlines()]
        for name in ['summary.json','missing.json','authorization.json']:
            shutil.copyfile(src/name,out/name)
        for name in ['responses.jsonl','attempts.json']:
            packed(src/name,out/(name+'.gz'))
        for p in src.glob('execution-*.json'):shutil.copyfile(p,out/p.name)
        for p in root.glob('endpoint-*.json'):shutil.copyfile(p,out/p.name)
        remaining={kind:max(0,m['counts'][kind if kind!='canary' else 'scheduled_canaries']-summary['global_valid'].get(kind,0)) for kind in ['primary','baseline','canary']}
        means={kind:sum(r['response']['usage']['cost'] for r in records if r['item']['kind']==kind)/sum(r['item']['kind']==kind for r in records)
               for kind in ['primary','baseline','canary'] if any(r['item']['kind']==kind for r in records)}
        validcost=sum(r['response']['usage']['cost'] for r in records)
        failure_rate=summary['failed_attempts']/max(len(attempts),1)
        remaining_cost=sum(remaining[k]*means.get(k,0) for k in remaining)*(1+failure_rate)
        rate=summary['valid_evaluations_per_second'];eta=sum(remaining.values())/rate if rate else None
        masses=[r['result']['binary_mass'] for r in records]
        latencies=[(datetime.fromisoformat(a['finished'])-datetime.fromisoformat(a['started'])).total_seconds() for a in attempts if a['finished']]
        report={'run_id':rid,'stage':stage,'status':summary['status'],'valid':summary['valid'],
            'physical_attempts':len(attempts),'failed_attempts':summary['failed_attempts'],
            'unknown_billing_attempts':sum(a['actual_cost'] is None for a in attempts),
            'http_status_counts':dict(Counter(str(a['http_status']) for a in attempts)),
            'failure_reasons':dict(Counter(a['error'] for a in attempts if a['error'])),
            'unresolved_evaluations':summary['missing'],'primary_physical_attempts':summary['primary_physical_attempts'],
            'stage_budget':summary['stage_budget'],'experiment_budget':summary['experiment_budget'],
            'cost_of_valid_records_usd':validcost,'remaining':remaining,'remaining_batches':len(m['batches'])-batch,
            'elapsed_seconds':summary['elapsed_seconds_this_invocation'],'valid_evaluations_per_second':rate,
            'primary_evaluations_per_second':summary['valid']['primary']/summary['elapsed_seconds_this_invocation'],
            'mean_attempt_latency_seconds':sum(latencies)/len(latencies) if latencies else None,
            'estimated_remaining_inference_seconds_at_observed_rate':eta,
            'estimated_remaining_cost_usd_at_observed_token_usage':remaining_cost,
            'estimated_total_cost_usd':summary['experiment_budget']['conservative_spending_usd']+remaining_cost,
            'projection_limitations':'Approx±20% token/throughput variation plus task startup overhead, throttling and price changes; not a guarantee or later-batch authorization.',
            'canary_max_conditional_probability_difference':summary['canary_max_probability_difference'],
            'canary_max_raw_logprob_difference':max((abs(r['result'][k]-r['item']['expected'][k]) for r in records if r['item']['kind']=='canary' for k in ['logp0','logp1']),default=None),
            'canary_max_log_odds_difference':max((abs(r['result']['log_odds']-r['item']['expected']['log_odds']) for r in records if r['item']['kind']=='canary'),default=None),
            'model_counts':dict(Counter(r['response']['model'] for r in records)),
            'provider_counts':dict(Counter(r['response']['provider'] for r in records)),
            'minimum_binary_mass':min(masses,default=None),'sampled_format_violations':sum(not r['result']['format_compliant'] for r in records),
            'prompt_tokens_all_attempts':sum((json.loads(a['response']) if a['response'] else {}).get('usage',{}).get('prompt_tokens',0) for a in attempts),
            'completion_tokens_all_attempts':sum((json.loads(a['response']) if a['response'] else {}).get('usage',{}).get('completion_tokens',0) for a in attempts),
            'later_batch_authorized':False,'checkpoint':'Authoritative SQLite transaction/WAL/FULL; stable experiment run+task keys; no valid evaluation recomputed.'}
        (out/'batch-report.json').write_text(json.dumps(report,indent=2)+'\n')
        backup=Path('/workspace/backups/granite-exploratory')/rid;backup.mkdir(parents=True,exist_ok=True)
        from granite_backup import create_snapshot
        db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True)
        try:create_snapshot(db,backup/(stage+'-ledger.sqlite'))
        finally:db.close()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);a=p.parse_args()
    print(json.dumps(preserve(a.batch),indent=2))
