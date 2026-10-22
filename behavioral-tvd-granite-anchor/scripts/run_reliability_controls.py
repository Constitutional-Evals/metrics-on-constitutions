"""Fixed near-zero/half/one selection, repeats and a 2x2 label/order control."""
import json,random
from pathlib import Path
from constitution_distance.core import digest
from constitution_distance.controls import control_request,probability_to_do
from constitution_distance.runner import validate_response,write_json
from constitution_distance.studies import run_study

BASE=Path('/workspace/work/finalization')


def validate(item,response):
    from argparse import Namespace
    p=validate_response(response,Namespace(model=item['request']['model']),{'endpoint':{'provider_name':'Parasail','context_length':131072}})
    return {'probabilities':p,'probability_to_do':probability_to_do(p,item['swapped'])}


def main():
    old=Path('/workspace/work/controlled-v2/pilot');manifest=json.loads((old/'manifest.json').read_text())
    rs=[json.loads(l) for l in (old/'responses.jsonl').read_text().splitlines()]
    scenarios={s['id']:s for s in manifest['spec']['scenarios']};chosen=[];items=[]
    for stratum,target in [('near_zero',0),('near_half',.5),('near_one',1)]:
        r=min(rs,key=lambda r:(abs(r['probabilities']['p1_conditional']-target),r['constitution_id'],int(r['scenario_id'])))
        chosen.append({'stratum':stratum,'constitution_id':r['constitution_id'],'scenario_id':r['scenario_id'],
                       'historical_probability':r['probabilities']['p1_conditional'],'historical_request_hash':r['request_hash']})
        for swapped in [False,True]:
            for reverse in [False,True]:
                request=control_request(r['request'],scenarios[r['scenario_id']],swapped=swapped,reverse_order=reverse)
                if not swapped and not reverse:assert digest(request)==r['request_hash']
                for replica in range(3):
                    items.append({'id':stratum+f'-swap{int(swapped)}-order{int(reverse)}','replica':replica,
                        'stratum':stratum,'constitution_id':r['constitution_id'],'scenario_id':r['scenario_id'],
                        'swapped':swapped,'reverse_order':reverse,'request':request})
    random.Random(20261021).shuffle(items)
    write_json(BASE/'reliability-selection.json',{'selection_rule':'closest existing pilot conditional p1 to 0, 0.5, 1; tie by constitution ID then numeric dilemma ID',
        'shuffle_seed':20261021,'pairs':chosen,'repeats_per_condition':3,'conditions':4,'max_dispatches':36,
        'design':'Full 2x2 label-association x action-line-order; original situations and action descriptions unchanged',
        'items_sha256':digest(items),'historical_selection_before_new_dispatch':True})
    records=run_study('numerical-reliability-label-order-2x2-v1',items,validate,
        ledger_path=BASE/'additional-budget.sqlite',output=BASE/'reliability-controls',budget=.95,concurrency=2)
    print('Reliability/control valid responses',len(records),'of',len(items),flush=True)

if __name__=='__main__':main()
