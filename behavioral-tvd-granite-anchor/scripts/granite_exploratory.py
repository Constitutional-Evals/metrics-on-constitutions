"""Prepare/dry-run or execute ONE explicitly authorized exploratory stage."""
import argparse
import collections
from decimal import Decimal
import gzip
import json
import math
import os
from pathlib import Path
import random
import shutil

from final_granite_pilot import request, validate
from constitution_distance.core import digest, load_constitutions, load_scenarios
from constitution_distance.exploratory import (BASELINE, CANARY, CONDITIONS, batch_items,
    canary_items, frozen_json, render, verify_manifest, run_batch)
from constitution_distance.local import file_hash

BUNDLE = Path('data/granite-exploratory')
CONFIG = Path('configs/granite-exploratory-approved.json')
RESULTS = Path('results/granite-exploratory')


def prepare():
    if CONFIG.exists():
        m = json.loads(CONFIG.read_text()); verify_manifest(m); return m
    BUNDLE.mkdir(parents=True, exist_ok=True)
    (BUNDLE/'constitutions').mkdir(exist_ok=True)
    for src,dst in [('data/scenarios-reviewed.jsonl', BUNDLE/'scenarios.jsonl'),
                    ('data/scenarios-v2.jsonl', BUNDLE/'original-library.jsonl')]:
        if dst.exists():
            if file_hash(src)!=file_hash(dst): raise ValueError('Frozen input copy mismatch')
        else: shutil.copyfile(src,dst)
    for source in sorted(Path('data/constitutions').glob('*.json')):
        dest=BUNDLE/'constitutions'/source.name
        if dest.exists():
            if file_hash(source)!=file_hash(dest): raise ValueError('Constitution snapshot mismatch')
        else: shutil.copyfile(source,dest)
    ss=load_scenarios(BUNDLE/'scenarios.jsonl'); original=load_scenarios(BUNDLE/'original-library.jsonl')
    cs={c['id']:c for c in load_constitutions(BUNDLE/'constitutions')}
    original_by={s['id']:s for s in original}; included={s['id'] for s in ss}
    assert len(ss)==1336 and len(original)==1360
    assert all(s==original_by[s['id']] for s in ss)
    assert all(set(s)=={'id','text','action1','action0','topic_group','topic'} for s in ss)
    audit={r['dilemma_id']:r for r in map(json.loads,Path('data/audit/scenario-audit.jsonl').read_text().splitlines())}
    excluded=[s for s in original if s['id'] not in included]
    assert len(excluded)==24 and all(audit[s['id']]['classification']=='valid' for s in ss)
    assert all(audit[s['id']]['classification']!='valid' for s in excluded)
    excluded_path=BUNDLE/'excluded-original-scenarios.json'
    frozen_json(excluded_path,{'scenarios':excluded,'dispositions':{s['id']:audit[s['id']]['classification'] for s in excluded}})
    approval={'execution_approved':True,'policy':'INVESTIGATOR_APPROVED_AUTOMATED_SCREENING',
        'individual_human_certification':False,'approved_scenario_count':1336,
        'approved_file_sha256':file_hash(BUNDLE/'scenarios.jsonl'),
        'included_ids':[s['id'] for s in ss],'excluded_ids':[s['id'] for s in excluded],
        'approval_basis':'Explicit investigator instruction: use1336provisionally valid scenarios, excludeall24flagged; no wording changes or individual human certification.',
        'interpretation':'Granite-conditioned geometry induced by24constitutional prompts; not established philosophical distances or perfect ethical implementation.'}
    frozen_json(BUNDLE/'approval.json',approval)
    old=[json.loads(line) for line in gzip.open('results/granite-final-pilot/evidence/canary-responses.jsonl.gz','rt')]
    by_hash={r['request_hash']:r for r in old}; assert len(by_hash)==6
    canaries=[]
    for h,r in sorted(by_hash.items()):
        cid,sid=r['item']['id'].removeprefix('canary--').rsplit('--',1)
        canaries.append({'request':r['request'],'request_hash':h,'constitution_id':cid,'scenario_id':sid,
                        'expected':{k:r['result'][k] for k in ['logp0','logp1','p1_conditional','log_odds']},
                        'pilot_cost':r['response']['usage']['cost']})
    ids=[s['id'] for s in ss]; random.Random(20261021).shuffle(ids)
    batches=[{'number':j//20+1,'scenario_ids':ids[j:j+20]} for j in range(0,len(ids),20)]
    settings={k:v for k,v in request([]).items() if k!='messages'}
    assert all(c['request']==render(settings,cs[c['constitution_id']],original_by[c['scenario_id']],0) for c in canaries)
    m={'schema_version':1,'experiment':'Granite-conditioned exploratory behavioral geometry',
       'scenario_approval':approval,'scenarios':ss,'constitutions':cs,'constitution_order':sorted(cs),
       'settings':settings,'conditions':[{'name':n,'swapped':s,'reverse_action_lines':r} for n,s,r in CONDITIONS],
       'replicates':1,'schedule_seed':20261021,'batches':batches,'canaries':canaries,
       'canary_schedule':'Six fixed prior-score requests before each500-evaluation chunk (480primary+20baseline), and at batch end. No later batch dispatch without authorization.',
       'resume_canary_policy':'If resuming an incomplete stage, first issue6fresh QC tasks bNNNN-resumeMMMM-cJJ, nextpersistedordinal. Priorvalidtasks are skipped; QC repetitions are separately identified and billed. AdditionalQC count is adaptive and remains underbothcaps.',
       'drift_thresholds':{'conditional_probability_absolute':.001,'log_odds_absolute':.01,'raw_label_logprob_absolute':.01},
       'probability':'Conditional over literalASCII0/1 from genuine next-token logs; rawlogs/unconditionalprobabilities/mass retained. Swapped mappings oriented to originalto_do.',
       'metrics':{'A_primary':'mean_s abs(mean_k p[c,s,k]-mean_k p[d,s,k])',
                  'B_secondary':'mean_k mean_s abs(p[c,s,k]-p[d,s,k])',
                  'C_robustness':'mean_s abs(p[c,s,canonical]-p[d,s,canonical])',
                  'summed_versions':'Multiply each normalized distance by includedscenario countN=1336; never conflateAandB.'},
       'execution':{'experiment_cap_usd':10,'stage_cap_usd':1,'concurrency':3,'max_attempts_per_evaluation':3,
          'max_primary_physical_attempts_per_stage':2000,'backoff_seconds':[2,4],
          'null_logs':'Only logprobs:null may be retried twice; non-null missing/malformed label logs stop. Every attempt recorded/budgeted.',
          'other_errors':'TransientHTTP/network errors bounded to3totalattempts; unknowncost chargedfullreservation. Identity/drift/malformedresponse stops batch.',
          'reservation':'110% of entire endpointcontextinputcost plusoneoutputtoken; experiment+stage caps include all concurrent reservations.',
          'budget_default_usd':0,'subsequent_batches_automatically_authorized':False},
       'numerical_limitation':'Observed0.125log-oddsgrid; exactrepeatability is not arbitraryprecision or constitutional fidelity.',
       'counts':{'scenarios':1336,'constitutions':24,'primary':128256,'baseline':5344,'batches':len(batches),
                 'scheduled_canaries':sum(((len(b['scenario_ids'])+4)//5+1)*6 for b in batches)}}
    m['counts']['total_including_canaries']=sum(m['counts'][k] for k in ['primary','baseline','scheduled_canaries'])
    # Preserve complete templates, including exact JSON escaping and system/user roles.
    placeholder={'id':'{id}','text':'{dilemma_situation}','action1':'{to_do_action}','action0':'{not_to_do_action}'}
    m['exact_template_examples']={n:{'constitutional':render(settings,{'constitution_json':'PLACEHOLDER'},placeholder,k)['messages'],
                                     'baseline':render(settings,{},placeholder,k,True)['messages']} for k,(n,_,_) in enumerate(CONDITIONS)}
    # Exhaustively compare all prior pilot requests against this renderer, without API calls.
    pilot=[json.loads(line) for line in gzip.open('results/granite-final-pilot/evidence/raw-final-responses.jsonl.gz','rt')]
    matches=0
    for r in pilot:
        i=r['item']
        if i['kind'] not in ['main','daily_baseline']: continue
        cid=i['constitution_id'];baseline=i['kind']=='daily_baseline';k=[n for n,_,_ in CONDITIONS].index(i['condition'])
        actual=render(settings,{} if baseline else cs[cid],original_by[i['scenario_id']],k,baseline)
        assert actual==r['request']; matches+=1
    assert matches==4000
    m['pilot_message_equivalence_checks']=matches
    plan=BUNDLE/'task-plan.jsonl.gz'
    with plan.open('wb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:
            for b in batches:
                group=batch_items(m,b['number'])+[i for r in range((len(b['scenario_ids'])+4)//5+1) for i in canary_items(m,b['number'],r)]
                for i in group:
                    row={k:i[k] for k in ['pair','kind','condition']};row.update({'batch':b['number'],'request_hash':digest(i['request']),'prompt_hash':digest(i['request']['messages'])})
                    z.write((json.dumps(row,sort_keys=True)+'\n').encode())
    source_paths=['src/constitution_distance/exploratory.py','scripts/granite_exploratory.py',
        'src/constitution_distance/core.py','src/constitution_distance/controls.py','src/constitution_distance/api.py',
        'src/constitution_distance/storage.py','src/constitution_distance/runner.py',
        'scripts/final_granite_pilot.py','scripts/cloud_api_comparison.py',
        'data/scenarios-reviewed.manifest.json','data/scenarios-v2.source.json','data/audit/scenario-audit.jsonl']
    m['file_sha256']={str(p):file_hash(p) for p in sorted(BUNDLE.rglob('*')) if p.is_file()}
    m['file_sha256'].update({p:file_hash(p) for p in source_paths})
    frozen_json(CONFIG,m)
    return m


def dry_run(m):
    verify_manifest(m); counts=collections.Counter();slots=set()
    for line in gzip.open(BUNDLE/'task-plan.jsonl.gz','rt'):
        i=json.loads(line);p=tuple(i['pair'])
        if p in slots: raise ValueError('Duplicate planned task identity')
        slots.add(p);counts[i['kind']]+=1
    assert counts['primary']==128256 and counts['baseline']==5344 and counts['canary']==2010
    assert len(slots)==135610
    pilot_cost=json.load(open('results/granite-final-pilot/full-cost-projection.json'))['estimates']['1336']['counterbalanced_cost_r1']
    baseline=[r for r in map(json.loads,gzip.open('results/granite-final-pilot/evidence/raw-final-responses.jsonl.gz','rt')) if r['item']['kind']=='daily_baseline']
    baseline_cost=sum(r['response']['usage']['cost'] for r in baseline)/len(baseline)*5344
    canary_cost=sum(c['pilot_cost'] for c in m['canaries'])/6*2010
    result={'run_id':digest(m),'api_requests':0,'inference_requests':0,'task_counts':dict(counts),
       'total_planned':len(slots),'batches':67,'first_batch':{'scenarios':20,'primary_logical':1920,
         'primary_physical_cap_including_retries':2000,'baseline':80,'canaries':30,'stage_cap_usd':1,'concurrency':3},
       'cost_estimate_usd':{'primary':pilot_cost,'baseline':baseline_cost,'canaries':canary_cost,
                            'total':pilot_cost+baseline_cost+canary_cost},
       'experiment_cap_usd':10,'reservation_usd_at131kcontext':float((Decimal('131000')*Decimal('.017')+Decimal('.112'))/1_000_000*Decimal('1.10')),
       'approved_scenario_policy':'Investigator-approved automated screen, no individual human certification',
       'excluded':24,'pilot_requests_exactly_matched':4000,'checks':'PASS: all135610taskidentities unique; snapshot/source hashes; originaltext/actions/topics preserved; frozen pilot messages; budgetsdefault0.'}
    RESULTS.mkdir(parents=True,exist_ok=True);frozen_json(RESULTS/'dry-run.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','dry-run','execute'])
    p.add_argument('--batch',type=int,default=1);p.add_argument('--experiment-budget-usd',type=float,default=0)
    p.add_argument('--stage-budget-usd',type=float,default=0);a=p.parse_args()
    os.chdir(Path(__file__).resolve().parents[1])
    m=prepare();rid=digest(m)
    if a.command in ['prepare','dry-run']:
        print(json.dumps(dry_run(m),indent=2))
    else:
        authpath=Path(f'configs/granite-exploratory-authorizations/batch-{a.batch:04d}.json')
        if not authpath.exists(): raise ValueError('No explicit authorization for this batch; no inference dispatched')
        auth=json.loads(authpath.read_text())
        print(json.dumps(run_batch(m,a.batch,Path('/workspace/work/granite-exploratory')/rid,auth,validate,
            experiment_budget=a.experiment_budget_usd,stage_budget=a.stage_budget_usd),indent=2))
