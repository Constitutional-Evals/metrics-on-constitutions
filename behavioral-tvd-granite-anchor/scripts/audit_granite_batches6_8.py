"""Read-only pre/post audit for exactly the investigator-authorized group 6–8."""
import argparse
import json
from pathlib import Path
import audit_granite_group


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);p.add_argument('--after',action='store_true');a=p.parse_args()
    assert a.batch in [6,7,8]
    result=audit_granite_group.prior.audit(a.batch,a.after)
    if a.batch==6 and not a.after:
        before=json.loads(Path('results/granite-exploratory/batch-0006/resumption-preflight.json').read_text())
        counts={k:sum(s['valid'][k] for s in before['prior_stages'].values()) for k in ['primary','baseline','canary']}
        assert counts=={'primary':9600,'baseline':400,'canary':162}
        assert result['spending_preserved_usd']==.507907266
    print(json.dumps(result,indent=2))
