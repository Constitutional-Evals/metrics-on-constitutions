"""Offline pre/post audit for exactly the approved sequential group 12–14."""
import argparse
import json
from pathlib import Path
import audit_granite_group

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);p.add_argument('--after',action='store_true');a=p.parse_args()
    assert a.batch in [12,13,14]
    result=audit_granite_group.prior.audit(a.batch,a.after)
    if a.batch==12 and not a.after:
        before=json.loads(Path('results/granite-exploratory/batch-0012/resumption-preflight.json').read_text())
        assert {k:sum(s['valid'][k] for s in before['prior_stages'].values()) for k in ['primary','baseline','canary']}=={'primary':21120,'baseline':880,'canary':342}
        assert result['spending_preserved_usd']==1.104767812
        assert sum(s['attempts'] for s in before['prior_stages'].values())==22350
    print(json.dumps(result,indent=2))
