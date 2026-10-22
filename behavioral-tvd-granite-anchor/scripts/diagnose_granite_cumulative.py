"""Offline pooled-prefix analysis plus prompt/baseline and geometry diagnostics."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from analyze_granite_cumulative import analyze
from analyze_granite_exploratory import matrix, table
from verify_granite_exploratory_batch import read
from constitution_distance.exploratory import CONDITIONS


def diagnose(through):
    assert through>=1
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text())
    assert through<=len(m['batches'])
    for b in range(1,through+1):
        assert json.loads(Path(f'results/granite-exploratory/batch-{b:04d}/summary.json').read_text())['status']=='COMPLETE'
    analysis=analyze(through)
    out=Path(f'results/granite-exploratory/cumulative-through-{through:04d}')
    cs,ids,_=read(out/'probabilities-counterbalanced.csv');n=len(ids)
    p=np.asarray([read(out/f'probabilities-{name}.csv')[2] for name,_,_ in CONDITIONS]);q=p.mean(0)
    rows=list(csv.DictReader((out/'baseline.csv').open()))
    assert [r['scenario'] for r in rows]==ids
    base=np.asarray([[float(r[name]) for r in rows] for name,_,_ in CONDITIONS]);bmean=base.mean(0)
    labels=(p[1]+p[3]-p[0]-p[2])/2;orders=(p[2]+p[3]-p[0]-p[1])/2
    shifts=q-bmean
    sensitivity=[]
    for i,c in enumerate(cs):
        sensitivity.append({'constitution':c,'mean_absolute_label_effect':float(abs(labels[i]).mean()),
                            'mean_absolute_order_effect':float(abs(orders[i]).mean()),
                            'mean_four_condition_range':float(np.ptp(p[:,i],axis=0).mean()),
                            'mean_four_condition_std':float(p[:,i].std(0).mean()),
                            'counterbalanced_mean_absolute_baseline_shift':float(abs(shifts[i]).mean()),
                            'counterbalanced_mean_signed_baseline_shift':float(shifts[i].mean()),
                            **{name+'_mean_absolute_baseline_shift':float(abs(p[k,i]-base[k]).mean()) for k,(name,_,_) in enumerate(CONDITIONS)}})
    table(out/'aggregate-prompt-and-baseline-sensitivity.csv',sensitivity)
    matrix(out/'constitution-baseline-shifts.csv',shifts,cs,ids)
    table(out/'scenario-prompt-sensitivity.csv',[{'constitution':c,'scenario':s,'label_effect':float(labels[i,j]),
          'order_effect':float(orders[i,j]),'four_condition_range':float(np.ptp(p[:,i,j]))} for i,c in enumerate(cs) for j,s in enumerate(ids)])
    tri=np.triu_indices(24,1);changes=[];pair_changes=[];neighbors=[];old=None
    for b in range(1,through+1):
        count=sum(len(x['scenario_ids']) for x in m['batches'][:b]);d=np.asarray(read(out/f'prefix-{count:04d}-distances-A_primary-normalized-l1.csv')[2])
        nearest=[min((j for j in range(24) if i!=j),key=lambda j:(d[i,j],cs[j])) for i in range(24)]
        for i,c in enumerate(cs):neighbors.append({'scenarios':count,'constitution':c,'nearest_neighbor':cs[nearest[i]],'normalized_A_distance':float(d[i,nearest[i]]),'changed_from_previous':None if old is None else nearest[i]!=old[1][i]})
        if old is not None:
            previous,prior_neighbors=old;delta=d-previous
            changes.append({'from_scenarios':count-len(m['batches'][b-1]['scenario_ids']),'to_scenarios':count,
                'mean_absolute_pairwise_A_distance_change':float(abs(delta[tri]).mean()),
                'maximum_absolute_pairwise_A_distance_change':float(abs(delta[tri]).max()),
                'mean_signed_pairwise_A_distance_change':float(delta[tri].mean()),
                'spearman_pair_distance_rank':float(spearmanr(previous[tri],d[tri]).statistic),
                'pearson_pair_distances':float(np.corrcoef(previous[tri],d[tri])[0,1]),
                'nearest_neighbors_unchanged':sum(a==b for a,b in zip(nearest,prior_neighbors))})
            for i,j in zip(*tri):pair_changes.append({'from_scenarios':count-len(m['batches'][b-1]['scenario_ids']),'to_scenarios':count,'constitution_a':cs[i],'constitution_b':cs[j],'previous_A_distance':float(previous[i,j]),'current_A_distance':float(d[i,j]),'signed_change':float(delta[i,j])})
        old=(d,nearest)
    table(out/'primary-geometry-changes.csv',changes);table(out/'primary-pairwise-distance-changes.csv',pair_changes)
    table(out/'primary-nearest-neighbor-evolution.csv',neighbors)
    summary={'run_id':analysis['run_id'],'scope':analysis['scope'],'full_experiment_complete':False,'api_requests':0,
             'mean_absolute_label_mapping_effect':float(abs(labels).mean()),'mean_absolute_action_order_effect':float(abs(orders).mean()),
             'mean_four_condition_range':float(np.ptp(p,axis=0).mean()),
             'mean_absolute_constitution_to_baseline_shift':float(abs(shifts).mean()),
             'mean_signed_constitution_to_baseline_shift':float(shifts.mean()),
             'constitution_mean_absolute_baseline_shift_min':float(abs(shifts).mean(1).min()),
             'constitution_mean_absolute_baseline_shift_max':float(abs(shifts).mean(1).max()),
             'primary_geometry_changes':changes,'scenario_subsampling':analysis['subsampling'],
             'interpretation':'Preliminary Granite-conditioned behavior over this completed scenario prefix. Counterbalancing does not remove all prompt sensitivity or establish philosophical fidelity.',
             'numerical_limitation':'Observed 0.125 log-odds quantization retained; no frozen inference/scientific code changed.'}
    (out/'scientific-diagnostics.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--through-batch',type=int,required=True);a=p.parse_args()
    print(json.dumps(diagnose(a.through_batch),indent=2))
