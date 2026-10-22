"""One explicitly authorized retry gate, then only missing slots; same task ledger/cap."""
import argparse,copy,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from final_granite_pilot import validate,BASE
from constitution_distance.core import digest
from constitution_distance.local import immutable_json,file_hash
from constitution_distance.storage import now
from constitution_distance.granite_pilot import run_pilot

p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
parent=json.load(open(BASE/'design-v2.json'));oldid=digest(parent);plan=json.load(open(BASE/'resume-review-plan.json'))
auth={'approved':True,'user_reply':'Retry once, then resume if valid','scope':'One exact gated retry; only if valid resume2653pending slots; same$.75ledger; stop on any further missing logs or drift. No completed responses recomputed.','parent_run_id':oldid,'failed_request_hash':plan['failure']['request_hash']}
if not (BASE/'resume-authorization.json').exists():immutable_json(BASE/'resume-authorization.json',{**auth,'recorded_at':now()})
items=copy.deepcopy(parent['items']);fail=next(i for i in items if i['id']==plan['failure']['slot'] and i['replica']==plan['failure']['replica']);items.remove(fail);fail['maximum_attempts']=1;items=[fail]+items
spec={**parent,'version':3,'amends_run_id':oldid,'amendment':'Explicit user-authorized one-attempt missing-logprob retry gate; if valid, only remaining requests. Same scientific payloads and predictions.','resume_authorization':auth,'runner_sha256':file_hash('src/constitution_distance/granite_pilot.py'),'resumption_sha256':file_hash(__file__),'items':items}
if (BASE/'design-v3.json').exists():
 if json.load(open(BASE/'design-v3.json'))!=spec:raise ValueError('Immutable authorized-resume design mismatch')
else:immutable_json(BASE/'design-v3.json',spec)
records=[json.loads(l) for l in (BASE/oldid/'responses.jsonl').read_text().splitlines()]
assert len(records)==1682 and digest(fail['request'])==plan['failure']['request_hash']
print('Authorized resume design',digest(spec),'import1682; gate1; pending2653',flush=True)
if a.execute:print(run_pilot(spec,validate,BASE,budget=.75,workers=6,adopt_records=records),flush=True)
