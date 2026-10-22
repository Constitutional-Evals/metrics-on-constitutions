"""New, isolated same-model backend/repeatability diagnostics under a shared $1 cap."""
import argparse,copy,json,math,random
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from constitution_distance.core import digest,extract_probabilities
from constitution_distance.runner import validate_response,write_json
from constitution_distance.studies import run_study

BASE=Path('/workspace/work/repro-diagnostics-2026-10-20')
SEED=20261020


def selected():
    rs=[json.loads(l) for l in Path('/workspace/work/controlled-v2/pilot/responses.jsonl').read_text().splitlines()]
    mid=[r for r in rs if .1<r['probabilities']['p1_conditional']<.9]
    low=sorted(rs,key=lambda r:(r['probabilities']['p1_conditional'],r['constitution_id'],int(r['scenario_id'])))[:3]
    high=sorted(rs,key=lambda r:(-r['probabilities']['p1_conditional'],r['constitution_id'],int(r['scenario_id'])))[:3]
    assert len(mid)==13 and len({(r['constitution_id'],r['scenario_id']) for r in mid+low+high})==19
    return mid+low+high


def endpoint(tag):
    obj=json.loads((BASE/'endpoints-before.json').read_text())
    return next(e for e in obj['data']['endpoints'] if e['tag']==tag)


def validate(item,response):
    p=validate_response(response,SimpleNamespace(model=item['request']['model']),{'endpoint':{
        'provider_name':item['expected_provider'],'context_length':item['context_length']}})
    independent=math.exp(p['logp1'])/(math.exp(p['logp0'])+math.exp(p['logp1']))
    if not math.isclose(independent,p['p1_conditional'],rel_tol=1e-12,abs_tol=1e-15):raise ValueError('Independent extraction mismatch')
    content=response['choices'][0]['logprobs']['content'][0]
    for label in ['0','1']:
        entries=[e for e in content['top_logprobs'] if e['token']==label]
        if entries and entries[0].get('bytes') not in (None,[ord(label)]):raise ValueError('Wrong token bytes')
    return {'probabilities':p,'log_odds':p['logp1']-p['logp0'],'independent_probability':independent}


def items_for(records,tag,condition,replicas=3,seeded=False):
    e=endpoint(tag);items=[]
    for index,r in enumerate(records):
        request=copy.deepcopy(r['request'])
        if tag!='parasail/fp8':
            request['provider']={'only':[tag],'allow_fallbacks':False,'require_parameters':True,
                'max_price':{'prompt':float(Decimal(e['pricing']['prompt'])*1_000_000),'completion':float(Decimal(e['pricing']['completion'])*1_000_000)}}
        if seeded:request['seed']=SEED
        for replica in range(replicas):
            items.append({'id':r['constitution_id']+'--'+r['scenario_id'],'replica':replica,
                'constitution_id':r['constitution_id'],'scenario_id':r['scenario_id'],
                'historical_probability':r['probabilities']['p1_conditional'],'historical_request_hash':r['request_hash'],
                'expected_provider':e['provider_name'],'context_length':e['context_length'],
                'condition':condition,'seeded':seeded,'request':request})
            if tag=='parasail/fp8' and not seeded:assert digest(request)==r['request_hash']
    random.Random(20261022).shuffle(items)
    return items


def execute(name,items,concurrency):
    write_json(BASE/(name+'-execution.json'),{'concurrency':concurrency,'items':len(items),
        'seed_parameter':SEED if all(i['seeded'] for i in items) else 'absent or mixed; inspect each saved request',
        'request_sequence_sha256':digest(items),'temperature':1,'top_p':1,'automatic_retries':0,
        'shared_budget_usd':1,'old_runs_modified':False})
    return run_study(name,items,validate,ledger_path=BASE/'budget.sqlite',output=BASE/name,budget=1,concurrency=concurrency)


def prepare():
    rs=selected()
    write_json(BASE/'selection.json',{'selection_rule':'all 13 pilot probabilities strictly between 0.1 and 0.9 plus lowest 3 and highest 3; ties by constitution then numeric dilemma ID',
        'selected':[{'constitution_id':r['constitution_id'],'scenario_id':r['scenario_id'],'pilot_p':r['probabilities']['p1_conditional'],'request_hash':r['request_hash']} for r in rs],
        'main_replicates_per_condition':3,'conditions':['seq-no-seed','conc-no-seed','seq-fixed-seed','conc-fixed-seed'],
        'seed':SEED,'primary_concurrent_workers':4,'targeted_anomaly_replicates':12,'short_controls':3,
        'interpretation':'Client concurrency does not control provider-side batching, caching or traffic; seed support is advertised, not a determinism guarantee.'})
    return rs


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['primary','probes','alternative'],required=True);p.add_argument('--provider')
    args=p.parse_args();rs=prepare()
    if args.stage=='primary':
        for name,workers,seeded in [('seq-no-seed',1,False),('conc-fixed-seed',4,True),('conc-no-seed',4,False),('seq-fixed-seed',1,True)]:
            execute(name,items_for(rs,'parasail/fp8',name,seeded=seeded),workers)
        anomaly=[r for r in rs if r['constitution_id']=='conservatism' and r['scenario_id']=='16204']
        for name,workers in [('anomaly-long-sequential',1),('anomaly-long-concurrent',4)]:
            items=items_for(anomaly,'parasail/fp8',name,replicas=12)+items_for(anomaly,'parasail/fp8',name+'-seed',replicas=12,seeded=True)
            # Distinct IDs avoid duplicate claims between seeded/unseeded groups.
            for item in items:
                if item['seeded']:item['id']+='--fixed-seed'
            random.Random(20261023).shuffle(items);execute(name,items,workers)
        short=[]
        prompts=[('short-true','Output exactly one ASCII digit: 1 if 2 + 2 = 4, otherwise 0. No other text.'),
            ('short-false','Output exactly one ASCII digit: 1 if 2 + 2 = 5, otherwise 0. No other text.'),
            ('short-neutral','Choose either of the two allowed answers, 0 or 1. Output exactly one ASCII digit and no other text.')]
        for sid,text in prompts:
            r=copy.deepcopy(rs[0]);r['constitution_id']='short-control';r['scenario_id']=sid
            r['request']['messages']=[{'role':'system','content':'Follow the output format exactly.'},{'role':'user','content':text}]
            r['request_hash']=digest(r['request']);short.append(r)
        for name,workers,seeded in [('short-seq',1,False),('short-conc',4,False),('short-seq-seed',1,True),('short-conc-seed',4,True)]:
            execute(name,items_for(short,'parasail/fp8',name,seeded=seeded),workers)
    elif args.stage=='probes':
        anomaly=[r for r in rs if r['constitution_id']=='conservatism' and r['scenario_id']=='16204']
        for tag in ['coreweave/fp16','novita/bf16']:
            name='probe-'+tag.replace('/','-')
            try:
                records=execute(name,items_for(anomaly,tag,name,replicas=1),1)
                print(tag,'valid:',len(records),flush=True)
            except (ValueError,RuntimeError) as exc:print(tag,'probe stopped:',str(exc),flush=True)
    else:
        if not args.provider:raise ValueError('An alternative provider must be explicitly selected; no automatic fallback')
        probe=BASE/('probe-'+args.provider.replace('/','-'))/'responses.jsonl'
        if not probe.exists() or not probe.read_text().strip():raise ValueError('Alternative provider has not passed live capability probe')
        for suffix,workers in [('seq',1),('conc',4)]:
            name=args.provider.replace('/','-')+'-comparison-'+suffix
            execute(name,items_for(rs,args.provider,name),workers)

if __name__=='__main__':main()
