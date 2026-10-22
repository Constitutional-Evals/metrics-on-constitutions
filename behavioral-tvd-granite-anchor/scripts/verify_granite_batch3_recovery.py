"""Independent completed-recovery checks, including actual token distributions."""
import gzip
import json
import math
from pathlib import Path

import numpy as np
from constitution_distance.core import digest
from constitution_distance.exploratory import frozen_json
from verify_granite_resumed_batch import verify


def verify_recovery():
    result=verify(3)  # Independent scalar A/B/C and frozen/adaptive request checks.
    out=Path('results/granite-exploratory/batch-0003');recovery=Path('results/granite-exploratory/batch-0003-recovery')
    prior=json.loads((recovery/'checkpoint-postcheck.json').read_text());assert prior['status']=='PASS'
    records=list(map(json.loads,gzip.open(out/'responses.jsonl.gz','rt')))
    maxerr=0.;masses=[];canary_raw=0.;canary_odds=0.
    for r in records:
        tokens=r['response']['choices'][0]['logprobs']['content'][0]['top_logprobs']
        logs={t['token']:t['logprob'] for t in tokens if t['token'] in ['0','1']}
        assert set(logs)=={'0','1'}
        for t in tokens:
            if t['token'] in ['0','1']:assert t['bytes']==[ord(t['token'])]
        a,b=math.exp(logs['0']),math.exp(logs['1']);q=b/(a+b)
        expected={'logp0':logs['0'],'logp1':logs['1'],'p0':a,'p1':b,'binary_mass':a+b,
                  'log_odds':logs['1']-logs['0'],'p1_conditional':q,
                  'p_to_do':1-q if r['item'].get('swapped',False) else q}
        for key,x in expected.items():
            maxerr=max(maxerr,abs(x-r['result'][key]));assert abs(x-r['result'][key])<1e-12
        if r['item']['kind']=='canary':
            canary_raw=max(canary_raw,*(abs(r['result'][k]-r['item']['expected'][k]) for k in ['logp0','logp1']))
            canary_odds=max(canary_odds,abs(r['result']['log_odds']-r['item']['expected']['log_odds']))
        else:masses.append(a+b)
    attempts=json.load(gzip.open(out/'attempts.json.gz','rt'))
    pre=json.loads((recovery/'preflight.json').read_text())
    failed=next(a for a in attempts if a['id']==pre['original_attempt_id'])
    assert digest(failed)==pre['original_attempt_sha256'] and failed['charged']==2449824 and failed['state']=='invalid'
    target=[a for a in attempts if (a['cid'],a['sid'],a['replica'])==('utilitarianism','2599',1)]
    assert len(target)==2 and sum(a['state']=='valid' for a in target)==1
    r=json.loads((out/'batch-report.json').read_text())
    r.update({'later_batch_authorized':False,'later_conditional_authorization_files_blocked':[4,5],
              'prompt_tokens_all_attempts':None,'completion_tokens_all_attempts':None,
              'usage_latency_note':'Original HTTP200 timeout envelope has no usage. Full reservation remains charged; original attempt timestamps were not manually settled or altered. Latency is client-recorded attempt lifetime, not isolated provider compute time.',
              'mean_attempt_latency_seconds':None,'scheduled_canaries':30,'adaptive_resume_canaries':6,
              'recovery_new_attempts':519,'recovery_failed_attempts':0,'recovery_request_phase_cost_usd':r['stage_budget']['conservative_spending_usd']-0.076831290,
              'binary_mass_quantiles':dict(zip(['min','q25','median','q75','max'],map(float,np.quantile(masses,[0,.25,.5,.75,1])))),
              'binary_mass_below_0_9':sum(x<.9 for x in masses),'maximum_independent_probability_error':maxerr})
    (out/'batch-report.json').write_text(json.dumps(r,indent=2)+'\n')
    result.update({'maximum_independent_probability_transformation_error':maxerr,'all_required_token_logs_available':True,
                   'all_required_tokens_have_literal_ASCII_bytes':True,'canary_max_raw_logprob_difference':canary_raw,
                   'canary_max_log_odds_difference':canary_odds,'original_failed_attempt_preserved_byte_for_byte_as_record':True,
                   'target_lifetime_attempt_count':2,'prior_batch3_valid_evaluations_preserved':1517,
                   'batch1_and_batch2_unchanged':True,'batch4_and_batch5_not_dispatched':True})
    (out/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    frozen_json(recovery/'completed-independent-verification.json',result)
    return result


if __name__=='__main__':print(json.dumps(verify_recovery(),indent=2))
