"""Offline diagnostics of complete pilot mass, repeats and label/order controls."""
from collections import Counter,defaultdict
import csv,json,math,statistics,sqlite3
from pathlib import Path
from constitution_distance.core import extract_probabilities,digest
from constitution_distance.runner import write_json

BASE=Path('/workspace/work/finalization')


def quantiles(values):
    x=sorted(values)
    def q(p):
        pos=(len(x)-1)*p;i=int(pos);j=min(i+1,len(x)-1)
        return x[i]+(x[j]-x[i])*(pos-i)
    return {'min':x[0],'p01':q(.01),'p05':q(.05),'median':q(.5),'mean':statistics.mean(x),
            'p95':q(.95),'p99':q(.99),'max':x[-1]}


def main():
    out=Path('results/methodology');out.mkdir(parents=True,exist_ok=True)
    pilot=[json.loads(l) for l in Path('/workspace/work/controlled-v2/pilot/responses.jsonl').read_text().splitlines()]
    assert len(pilot)==480
    rows=[]
    for r in pilot:
        p=extract_probabilities(r['response']);assert p==r['probabilities']
        rows.append({'constitution_id':r['constitution_id'],'dilemma_id':r['scenario_id'],
            'logp0':p['logp0'],'logp1':p['logp1'],'p0':p['p0'],'p1':p['p1'],
            'binary_mass':p['binary_mass'],'p1_conditional':p['p1_conditional'],
            'substantial_other_mass_0_05':p['binary_mass']<.95})
    with (out/'pilot-binary-mass.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
    mass={'distribution':quantiles([r['binary_mass'] for r in rows]),
        'below_0_95':[r for r in rows if r['binary_mass']<.95],
        'below_0_99_count':sum(r['binary_mass']<.99 for r in rows),
        'above_one_due_to_precision_count':sum(r['binary_mass']>1 for r in rows),
        'rounding_tolerance':1e-5,'raw_values_preserved':True}
    rs=[json.loads(l) for l in (BASE/'reliability-controls/responses.jsonl').read_text().splitlines()]
    groups=defaultdict(list)
    for r in rs:
        i=r['item'];assert r['request_hash']==digest(r['request'])
        groups[(i['stratum'],i['swapped'],i['reverse_order'])].append(r)
    table=[]
    for key,records in sorted(groups.items()):
        hashes={r['request_hash'] for r in records};assert len(hashes)==1
        values=[r['result']['probability_to_do'] for r in records]
        table.append({'stratum':key[0],'swapped':key[1],'reverse_order':key[2],
            'constitution_id':records[0]['item']['constitution_id'],'dilemma_id':records[0]['item']['scenario_id'],
            'n':len(values),'mean':statistics.mean(values),'min':min(values),'max':max(values),
            'absolute_range':max(values)-min(values),'population_stddev':statistics.pstdev(values),
            'identical':len(set(values))==1,'request_hash':next(iter(hashes))})
    with (out/'reliability-label-order-summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator="\n");w.writeheader();w.writerows(table)
    comparisons=[]
    for stratum in ['near_zero','near_half','near_one']:
        cells={(r['swapped'],r['reverse_order']):r for r in table if r['stratum']==stratum}
        baseline=cells[(False,False)]['mean']
        comparisons.append({'stratum':stratum,
            'canonical_mean':baseline,'canonical_range':cells[(False,False)]['absolute_range'],
            'label_swap_fixed_action_order_mean':cells[(True,False)]['mean'],
            'label_swap_fixed_action_order_delta':cells[(True,False)]['mean']-baseline,
            'order_only_mean':cells[(False,True)]['mean'],
            'order_only_delta':cells[(False,True)]['mean']-baseline,
            'label_swap_same_numeric_order_mean':cells[(True,True)]['mean'],
            'label_swap_same_numeric_order_delta':cells[(True,True)]['mean']-baseline,
            'max_condition_mean_difference':max(c['mean'] for c in cells.values())-min(c['mean'] for c in cells.values())})
    c=sqlite3.connect(BASE/'additional-budget.sqlite')
    costs={'auxiliary_known_cost_usd':c.execute('select sum(charged)/1e9 from attempts').fetchone()[0],
        'auxiliary_dispatches':c.execute('select count(*) from attempts').fetchone()[0],
        'auxiliary_unknown_cost_count':c.execute('select count(*) from attempts where actual_cost is null').fetchone()[0],
        'auxiliary_fixed_cap_usd':c.execute('select cap/1e9 from settings where id=1').fetchone()[0],
        'missing_pilot_completion_cost_usd':.0006176,'additional_task_cap_usd':1,
        'combined_new_actual_cost_usd':c.execute('select sum(charged)/1e9 from attempts').fetchone()[0]+.0006176,
        'numerical_and_swap_cost_usd':c.execute("select sum(charged)/1e9 from attempts a join runs r on a.run=r.id where json_extract(r.spec,'$.name')='numerical-reliability-label-order-2x2-v1'").fetchone()[0]}
    c.close()
    result={'pilot_binary_mass':mass,'fixed_selection':json.loads((BASE/'reliability-selection.json').read_text()),
        'control_summary':table,'comparisons':comparisons,'costs':costs,
        'all_36_numeric_responses_valid':len(rs)==36,
        'model_provider':{'model':'meta-llama/llama-3.3-70b-instruct','endpoint':'parasail/fp8'},
        'interpretation':'Strong numerical instability and label/order sensitivity in the near-half diagnostic. Three selected pairs and three repeats per cell do not estimate population-wide bias. No automatic design/model/provider change is made.'}
    write_json(out/'reliability-analysis.json',result)
    print(json.dumps({'mass':mass,'comparisons':comparisons,'costs':costs},indent=2))

if __name__=='__main__':main()
