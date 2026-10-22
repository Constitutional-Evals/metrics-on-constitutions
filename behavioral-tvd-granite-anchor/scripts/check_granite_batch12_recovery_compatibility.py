"""Exercise the unchanged runner's claims on a disposable restored ledger only."""
import json
from pathlib import Path
import tempfile
from constitution_distance.core import digest
from constitution_distance.exploratory import StageLedger,resume_canary_items,frozen_json
from constitution_distance.local import file_hash
from granite_backup import restore_to
from recover_granite_batch12_timeout import ROOT,OUT,RID,PAIR,AID,connect,fingerprints


def check():
    pre=json.loads((OUT/'preflight.json').read_text())
    with tempfile.TemporaryDirectory(dir='/workspace/backups',prefix='batch12-compatibility-') as td:
        path=Path(td)/'ledger.sqlite';restore_to(pre['archive_path'],path)
        assert file_hash(path)==pre['backup_sha256']
        ledger=StageLedger(path,10)
        try:
            row=ledger.db.execute('SELECT * FROM attempts WHERE id=?',(AID,)).fetchone();original=dict(row)
            assert digest(original)==pre['original_attempt_sha256']
            request=json.loads(row['request'])
            ledger.db.execute("UPDATE evaluations SET state='retry' WHERE run=? AND cid=? AND sid=? AND replica=? AND state='invalid' AND record IS NULL",(RID,*PAIR))
            aid=ledger.claim_stage('batch-0012',RID,PAIR,request,2449824,retry=True);assert aid
            assert ledger.db.execute('SELECT COUNT(*) FROM attempts WHERE run=? AND cid=? AND sid=? AND replica=?',(RID,*PAIR)).fetchone()[0]==2
            assert dict(ledger.db.execute('SELECT * FROM attempts WHERE id=?',(AID,)).fetchone())==original
            assert ledger.claim_stage('batch-0012',RID,PAIR,request,2449824,retry=True) is None
            v=ledger.db.execute("SELECT cid,sid,replica,record FROM evaluations WHERE state='valid' LIMIT 1").fetchone()
            assert ledger.claim_stage('batch-0012',RID,tuple(v[:3]),json.loads(v['record'])['request'],2449824,retry=True) is None
            assert ledger.db.execute("SELECT cap,primary_cap FROM dispatch_stages WHERE id='batch-0012'").fetchone()[:]==(1000000000,2000)
            assert ledger.db.execute("SELECT COUNT(*) FROM evaluations WHERE cid='__canary__' AND sid LIKE 'b0012-resume%'").fetchone()[0]==0
            m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());assert len(resume_canary_items(m,12,1))==6
        finally:ledger.close()
    c=connect()
    try:assert fingerprints(c)==pre['fingerprints']
    finally:c.close()
    result={'status':'PASS','api_requests':0,'disposable_copy_only':True,'authoritative_state_unchanged':True,
            'existing_claim_stage_accepts_retry':True,'valid_checkpoint_claim_refused':True,'duplicate_claim_refused':True,
            'original_attempt_retained':True,'retry_will_be_physical_attempt_number':2,'lifetime_maximum_attempts':3,
            'required_fresh_resume_canaries':6,'original_stage_caps_unchanged':True}
    frozen_json(OUT/'runner-compatibility.json',result);return result


if __name__=='__main__':print(json.dumps(check(),indent=2))
