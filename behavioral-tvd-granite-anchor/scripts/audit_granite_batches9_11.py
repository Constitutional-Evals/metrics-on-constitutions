"""Offline cross-task audit for exactly the approved sequential group 9–11."""
import argparse
import json
from pathlib import Path
import audit_granite_group

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);p.add_argument('--after',action='store_true');a=p.parse_args()
    assert a.batch in [9,10,11]
    result=audit_granite_group.prior.audit(a.batch,a.after)
    if a.batch==9 and not a.after:
        before=json.loads(Path('results/granite-exploratory/batch-0009/resumption-preflight.json').read_text())
        assert {k:sum(s['valid'][k] for s in before['prior_stages'].values()) for k in ['primary','baseline','canary']}=={'primary':15360,'baseline':640,'canary':252}
        assert result['spending_preserved_usd']==.806481692
    print(json.dumps(result,indent=2))
