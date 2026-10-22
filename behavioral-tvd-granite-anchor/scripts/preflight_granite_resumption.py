"""Read-only cross-task audit; refuse missing ledgers before any API operation."""
import argparse
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

from constitution_distance.core import digest
from constitution_distance.exploratory import batch_items,canary_items,frozen_json,verify_manifest
from constitution_distance.local import file_hash
from final_granite_pilot import validate

EXPECTED='03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e'


def snapshot(db,root,m,batch):
    stage=f'batch-{batch:04d}';items=batch_items(m,batch)
    rounds=(len(m['batches'][batch-1]['scenario_ids'])+4)//5+1
    items += [i for r in range(rounds) for i in canary_items(m,batch,r)]
    curated={tuple(r['item']['pair']):r for r in map(json.loads,gzip.open(f'results/granite-exploratory/{stage}/responses.jsonl.gz','rt'))}
    evaluations={};counts={'primary':0,'baseline':0,'canary':0}
    for item in items:
        pair=tuple(item['pair']);row=db.execute('SELECT * FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(EXPECTED,*pair)).fetchone()
        assert row is not None and row['state']=='valid','Prior stage has missing/invalid checkpoint'
        record=json.loads(row['record']);assert record==curated[pair],'Curated evidence differs from authoritative checkpoint'
        assert record['request']==item['request'] and record['request_hash']==digest(item['request'])
        assert record['prompt_hash']==digest(item['request']['messages'])
        assert record['result']==validate(item,record['response'])
        assert record['response']['model']==m['settings']['model'] and record['response']['provider']=='Cloudflare'
        evaluations[json.dumps(pair)]=digest(dict(row));counts[item['kind']]+=1
    archived=json.load(gzip.open(f'results/granite-exploratory/{stage}/attempts.json.gz','rt'))
    attempts=[dict(row) for row in db.execute('SELECT a.* FROM attempts a JOIN stage_attempts s ON s.aid=a.id WHERE s.stage=? ORDER BY a.started,a.id',(stage,))]
    assert attempts==archived,'Prior paid-attempt history differs from curated archive'
    cfg=dict(db.execute('SELECT * FROM dispatch_stages WHERE id=?',(stage,)).fetchone())
    assert cfg['run']==EXPECTED and cfg['cap']==1_000_000_000 and cfg['primary_cap']==2000
    files={str(p):file_hash(p) for parent in [root/stage,Path('results/granite-exploratory')/stage] for p in sorted(parent.rglob('*')) if p.is_file()}
    return {'valid':counts,'evaluation_row_sha256':evaluations,'attempt_row_sha256':{r['id']:digest(r) for r in attempts},
            'stage_configuration_sha256':digest(cfg),'files_sha256':files,
            'attempts':len(attempts),'charged_nanos':sum(r['charged'] for r in attempts)}


def audit(batch,after=False):
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text())
    assert digest(m)==EXPECTED,'Unexpected frozen run ID';verify_manifest(m)
    root=Path('/workspace/work/granite-exploratory')/EXPECTED
    assert (root/'ledger.sqlite').is_file() and (root/'manifest.json').is_file(),'Original authoritative state unavailable; stop without network'
    assert json.loads((root/'manifest.json').read_text())==m,'Operational manifest differs'
    output=Path('results/granite-exploratory')/f'batch-{batch:04d}';beforefile=output/'resumption-preflight.json'
    with (root/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert db.execute('SELECT cap FROM settings').fetchone()[0]==10_000_000_000
            runs=list(db.execute('SELECT id,spec FROM runs'));assert len(runs)==1 and runs[0]['id']==EXPECTED and json.loads(runs[0]['spec'])==m
            assert db.execute("SELECT COUNT(*) FROM attempts WHERE state='reserved'").fetchone()[0]==0
            assert db.execute("SELECT COUNT(*) FROM evaluations WHERE state='inflight'").fetchone()[0]==0
            priors={f'batch-{j:04d}':snapshot(db,root,m,j) for j in range(1,batch)}
            if after:
                before=json.loads(beforefile.read_text());assert before['prior_stages']==priors,'Prior-stage records changed'
                assert all(file_hash(p)==h for p,h in before['preexisting_tracked_files_sha256'].items()),'Pre-existing tracked file changed'
                assert db.execute('SELECT cap FROM settings').fetchone()[0]==before['global_cap_nanos']
                report={'status':'PASS','api_requests':0,'run_id':EXPECTED,'batch':batch,'prior_stage_records_unchanged':True,
                    'preexisting_tracked_files_unchanged':len(before['preexisting_tracked_files_sha256']),
                    'prior_attempts_preserved':sum(s['attempts'] for s in priors.values()),'global_budget_preserved_usd':10}
                frozen_json(output/'prior-records-postcheck.json',report);return report
            assert set(r['id'] for r in db.execute('SELECT id FROM dispatch_stages'))==set(priors),'Unexpected registered stages; stop for review'
            charged=db.execute('SELECT COALESCE(SUM(charged),0) FROM attempts').fetchone()[0]
            assert charged==sum(s['charged_nanos'] for s in priors.values()),'Spending history mismatch'
            for j,s in priors.items():
                assert s['charged_nanos']==round(json.loads((Path('results/granite-exploratory')/j/'summary.json').read_text())['stage_budget']['conservative_spending_usd']*1e9)
            current=batch_items(m,batch)+[i for r in range((len(m['batches'][batch-1]['scenario_ids'])+4)//5+1) for i in canary_items(m,batch,r)]
            for i in current:
                p=tuple(i['pair']);row=db.execute('SELECT state,record FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(EXPECTED,*p)).fetchone()
                assert row is not None and row['state']=='pending' and row['record'] is None,'New batch has prior work: review before dispatch'
            files=[p for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p]
            report={'status':'PASS','api_requests':0,'run_id':EXPECTED,'protocol_commit':'a8c1a66998c07cfaa1a1b07f016ae21259b34bee',
                'global_cap_nanos':10_000_000_000,'spending_preserved_usd':charged/1e9,'sqlite_integrity_check':'ok',
                'prior_stages':priors,'preexisting_tracked_files_sha256':{p:file_hash(p) for p in files},
                'next_batch':batch,'scenario_ids':m['batches'][batch-1]['scenario_ids'],'next_batch_pending_tasks':len(current),
                'original_ledger_preserved':True,'replacement_ledger_created':False}
            backup=Path('/workspace/backups/granite-exploratory')/EXPECTED;backup.mkdir(parents=True,exist_ok=True)
            from granite_backup import prior_snapshot
            report['before_stage_backup']=prior_snapshot(db,backup,batch)
            frozen_json(beforefile,report)
            return {k:v for k,v in report.items() if k not in ['prior_stages','preexisting_tracked_files_sha256']}
        finally:db.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);p.add_argument('--after',action='store_true');a=p.parse_args()
    print(json.dumps(audit(a.batch,a.after),indent=2))
