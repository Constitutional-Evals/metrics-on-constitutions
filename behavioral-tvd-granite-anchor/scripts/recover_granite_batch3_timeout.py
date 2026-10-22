"""Explicit, one-checkpoint recovery authorized by the investigator.

No API calls. The frozen dispatcher and every historical attempt stay unchanged.
Verification precedes a consistent backup; recovery uses its own exclusive lock,
BEGIN IMMEDIATE transaction, exact-state checks and independent audit records.
"""
import argparse
from collections import Counter
import fcntl
import gzip
import json
from pathlib import Path
import sqlite3
import uuid

from audit_granite_group import snapshot
from constitution_distance.core import digest
from constitution_distance.exploratory import batch_items, canary_items, frozen_json, verify_manifest
from constitution_distance.local import file_hash
from constitution_distance.storage import now

RID='03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e'
PAIR=('utilitarianism','2599',1)
AID='8be8073b7d154c2b9d33af2403aaf96e'
ROOT=Path('/workspace/work/granite-exploratory')/RID
OUT=Path('results/granite-exploratory/batch-0003-recovery')


def connect(write=False):
    assert (ROOT/'ledger.sqlite').is_file(), 'Authoritative ledger unavailable; no replacement permitted'
    c=sqlite3.connect(f'file:{ROOT}/ledger.sqlite?mode={"rw" if write else "ro"}',uri=True,isolation_level=None)
    c.row_factory=sqlite3.Row
    return c


def verify(c):
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text())
    assert digest(m)==RID;verify_manifest(m)
    assert json.loads((ROOT/'manifest.json').read_text())==m
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert c.execute('SELECT cap FROM settings').fetchone()[0]==10_000_000_000
    assert c.execute('SELECT SUM(charged) FROM attempts').fetchone()[0]==283413186
    assert c.execute("SELECT COUNT(*) FROM attempts WHERE state='reserved'").fetchone()[0]==0
    assert c.execute("SELECT COUNT(*) FROM evaluations WHERE state='inflight'").fetchone()[0]==0
    assert [r[0] for r in c.execute('SELECT id FROM dispatch_stages ORDER BY id')]==['batch-0001','batch-0002','batch-0003']
    assert c.execute("SELECT cap,primary_cap FROM dispatch_stages WHERE id='batch-0003'").fetchone()[:]==(1_000_000_000,2000)
    runs=list(c.execute('SELECT id,spec FROM runs'));assert len(runs)==1 and runs[0]['id']==RID and json.loads(runs[0]['spec'])==m
    old=json.loads(Path('results/granite-exploratory/batch-0003/resumption-preflight.json').read_text())
    priors={f'batch-{b:04d}':snapshot(c,ROOT,m,b) for b in [1,2]}
    assert priors==old['prior_stages'], 'Prior batches changed'
    archived=list(map(json.loads,gzip.open('results/granite-exploratory/batch-0003/responses.jsonl.gz','rt')))
    archived_attempts=json.load(gzip.open('results/granite-exploratory/batch-0003/attempts.json.gz','rt'))
    actual_attempts=[dict(r) for r in c.execute("SELECT a.* FROM attempts a JOIN stage_attempts s ON s.aid=a.id WHERE s.stage='batch-0003' ORDER BY a.started,a.id")]
    assert actual_attempts==archived_attempts
    assert len(archived)==1517 and Counter(r['item']['kind'] for r in archived)=={'primary':1439,'baseline':60,'canary':18}
    for r in archived:
        row=c.execute('SELECT state,record FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(RID,*r['item']['pair'])).fetchone()
        assert row['state']=='valid' and json.loads(row['record'])==r
    items=batch_items(m,3)+[i for k in range(5) for i in canary_items(m,3,k)]
    pending=[]
    for item in items:
        row=c.execute('SELECT * FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(RID,*item['pair'])).fetchone()
        if row['state']!='valid':pending.append(dict(row))
    assert len(pending)==513
    invalid=list(c.execute("SELECT * FROM evaluations WHERE state='invalid'"))
    assert len(invalid)==1 and tuple(invalid[0][k] for k in ['cid','sid','replica'])==PAIR and invalid[0]['record'] is None
    a=dict(c.execute('SELECT * FROM attempts WHERE id=?',(AID,)).fetchone())
    assert a==next(r for r in archived_attempts if r['id']==AID)
    assert (a['run'],a['cid'],a['sid'],a['replica'],a['state'],a['error'],a['http_status'],a['charged'],a['actual_cost'])==(RID,*PAIR,'invalid','Model/provider mismatch',200,2449824,None)
    assert c.execute('SELECT COUNT(*) FROM attempts WHERE run=? AND cid=? AND sid=? AND replica=?',(RID,*PAIR)).fetchone()[0]==1
    response=json.loads(a['response'])
    assert response['error']=={'message':'Upstream idle timeout exceeded','code':504,'metadata':{'error_type':'timeout'}}
    assert response.get('_http_status')==200
    assert all(response.get(k) is None for k in ['model','provider','choices','usage'])
    expected=next(i['request'] for i in items if tuple(i['pair'])==PAIR)
    assert json.loads(a['request'])==expected and a['prompt_hash']==digest(expected['messages'])
    return m,priors,a,dict(invalid[0])


def fingerprints(c):
    valid={json.dumps([r['cid'],r['sid'],r['replica']]):digest(dict(r)) for r in c.execute("SELECT * FROM evaluations WHERE state='valid'")}
    attempts={r['id']:digest(dict(r)) for r in c.execute('SELECT * FROM attempts')}
    return {'valid_evaluations':valid,'attempts':attempts}


def preflight():
    assert not (OUT/'preflight.json').exists(), 'Preflight already preserved; inspect rather than replace'
    with (ROOT/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        c=connect()
        try:
            m,priors,a,row=verify(c)
            backup=Path('/workspace/backups/granite-exploratory')/RID/'before-batch-0003-reviewed-recovery.sqlite'
            assert not backup.exists();t=sqlite3.connect(backup);c.backup(t)
            assert t.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            t.row_factory=sqlite3.Row;assert fingerprints(t)==fingerprints(c);t.close()
            result={'status':'PASS','run_id':RID,'api_requests':0,'verified_at':now(),'prior_stages':priors,
                    'batch3_valid':{'primary':1439,'baseline':60,'canary':18},'scheduled_missing':513,
                    'global_cap_nanos':10_000_000_000,'conservative_charged_nanos':283413186,'reserved_nanos':0,
                    'target_evaluation':row,'original_attempt_id':AID,'original_attempt_sha256':digest(a),
                    'request_sha256':digest(json.loads(a['request'])),'response_sha256':digest(json.loads(a['response'])),
                    'backup_path':str(backup),'backup_sha256':file_hash(backup),'fingerprints':fingerprints(c)}
            frozen_json(OUT/'preflight.json',result)
            return {k:v for k,v in result.items() if k not in ['prior_stages','fingerprints']}
        finally:c.close()


def recover():
    pre=json.loads((OUT/'preflight.json').read_text())
    assert file_hash(pre['backup_path'])==pre['backup_sha256']
    with (ROOT/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        c=connect(write=True)
        try:
            _,_,a,row=verify(c);assert fingerprints(c)==pre['fingerprints']
            txid=uuid.uuid4().hex
            intent={'transaction_id':txid,'created_at':now(),'run_id':RID,'key':[RID,*PAIR],
                    'authorization':'Investigator pasted request: reviewed recovery of this exact HTTP200/internal504 timeout, then Batch3ONLY; noBatch4or5.',
                    'reason':'Reviewed transient upstream timeout without model output; not evidence of a provider switch.',
                    'before':row,'transition':'invalid -> retry','original_attempt_id':AID,
                    'original_attempt_sha256':digest(a),'original_charge_nanos':2449824,
                    'atomic_transaction':'BEGIN IMMEDIATE; guarded single evaluation UPDATE; COMMIT',
                    'historical_attempts_modified':False,'frozen_dispatcher_modified':False}
            frozen_json(OUT/'recovery-intent.json',intent);frozen_json(ROOT/'batch-0003-reviewed-recovery-intent.json',intent)
            c.execute('PRAGMA synchronous=FULL');c.execute('BEGIN IMMEDIATE')
            try:
                assert dict(c.execute('SELECT * FROM attempts WHERE id=?',(AID,)).fetchone())==a
                assert dict(c.execute('SELECT * FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(RID,*PAIR)).fetchone())==row
                cursor=c.execute("UPDATE evaluations SET state='retry' WHERE run=? AND cid=? AND sid=? AND replica=? AND state='invalid' AND record IS NULL",(RID,*PAIR))
                assert cursor.rowcount==1 and c.total_changes==1
                assert fingerprints(c)==pre['fingerprints']
                c.execute('COMMIT')
            except BaseException:c.execute('ROLLBACK');raise
            after=dict(c.execute('SELECT * FROM evaluations WHERE run=? AND cid=? AND sid=? AND replica=?',(RID,*PAIR)).fetchone())
            assert after==dict(row,state='retry')
            assert c.execute('SELECT SUM(charged) FROM attempts').fetchone()[0]==283413186
            result=dict(intent,status='COMMITTED',committed_at=now(),after=after,
                        sql_rows_changed=c.total_changes,original_attempt_unchanged=True,all_preexisting_valid_rows_unchanged=True,
                        spending_unchanged=True,remaining_lifetime_attempts=2,
                        runner_compatibility='Existing runner rejects invalid/error, accepts retry, counts one prior physical attempt and uses claim_stage(retry=True); six fresh resume canaries run first.')
            frozen_json(OUT/'recovery-committed.json',result);frozen_json(ROOT/'batch-0003-reviewed-recovery-committed.json',result)
            return result
        finally:c.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['verify','recover']);args=p.parse_args()
    print(json.dumps(preflight() if args.command=='verify' else recover(),indent=2))
