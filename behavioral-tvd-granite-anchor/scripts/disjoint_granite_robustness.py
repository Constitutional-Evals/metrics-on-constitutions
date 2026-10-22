"""Descriptive, offline disjoint-subset check of pooled primary A geometry.

The frozen scenario schedule is divided into two consecutive equal halves.
No data-dependent selection, inference, checkpoint mutation or imputation.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from analyze_granite_exploratory import matrix,table
from verify_granite_exploratory_batch import read


def compare(q,constitutions,ids):
    q=np.asarray(q,dtype=float)
    if q.shape!=(len(constitutions),len(ids)) or len(ids)%2 or len(ids)<4:
        raise ValueError('Complete, even-sized scenario grid required')
    if not np.isfinite(q).all() or not ((q>=0)&(q<=1)).all():
        raise ValueError('Missing or invalid probability: no disjoint analysis')
    if len(set(ids))!=len(ids):raise ValueError('Scenario identities must be unique')
    half=len(ids)//2
    groups=[q[:,:half],q[:,half:]]
    distances=[abs(v[:,None,:]-v[None,:,:]).mean(-1) for v in groups]
    maxerr=0.
    for v,d in zip(groups,distances):
        assert np.array_equal(d,d.T) and (d.diagonal()==0).all() and (d>=0).all()
        for i in range(len(constitutions)):
            for j in range(len(constitutions)):
                expected=math.fsum(abs(v[i,s]-v[j,s]) for s in range(half))/half
                maxerr=max(maxerr,abs(expected-d[i,j]));assert abs(expected-d[i,j])<1e-12
    tri=np.triu_indices(len(constitutions),1);a,b=[d[tri] for d in distances]
    rank=float(spearmanr(a,b).statistic)
    if not math.isfinite(rank):raise ValueError('Degenerate distance ranking; correlation undefined')
    neighbors=[[min((j for j in range(len(constitutions)) if j!=i),key=lambda j:(d[i,j],constitutions[j]))
                for i in range(len(constitutions))] for d in distances]
    absolute=abs(a-b)
    summary={'scenario_count_each':half,'first_scenario_ids':ids[:half],'next_scenario_ids':ids[half:],
             'scenario_overlap_count':len(set(ids[:half])&set(ids[half:])),
             'primary_A_distance_spearman':rank,'mean_absolute_normalized_distance_difference':float(absolute.mean()),
             'median_absolute_normalized_distance_difference':float(np.median(absolute)),
             'maximum_absolute_normalized_distance_difference':float(absolute.max()),
             'mean_signed_second_minus_first_distance':float((b-a).mean()),
             'nearest_neighbor_agreement_count':sum(x==y for x,y in zip(*neighbors)),
             'nearest_neighbor_agreement_fraction':sum(x==y for x,y in zip(*neighbors))/len(constitutions),
             'first_mean_normalized_A_distance':float(a.mean()),'next_mean_normalized_A_distance':float(b.mean()),
             'maximum_independent_scalar_error':maxerr,
             'selection':'First half versus next half of the frozen completed scenario schedule; no reselection.',
             'dependence_note':'Nested cumulative comparisons reuse earlier scenarios and are statistically dependent; their apparent stability can partly reflect shared observations. These two scenario subsets are disjoint, but still share the model, constitutions and collection procedure. This descriptive check is not a population-level independence or validity claim.'}
    return distances,neighbors,summary


def analyze(through):
    out=Path(f'results/granite-exploratory/cumulative-through-{through:04d}')
    manifest=json.loads((out/'analysis-summary.json').read_text())
    cs,ids,q=read(out/'probabilities-counterbalanced.csv');distances,neighbors,summary=compare(q,cs,ids)
    n=summary['scenario_count_each'];subset=out/f'disjoint-first-{n:04d}-vs-next-{n:04d}';subset.mkdir(exist_ok=True)
    for label,d in zip(['first','next'],distances):
        matrix(subset/f'{label}-distances-A-normalized-l1.csv',d,cs,cs)
        matrix(subset/f'{label}-distances-A-summed-l1.csv',d*n,cs,cs)
    table(subset/'nearest-neighbors.csv',[{'constitution':c,'first_neighbor':cs[neighbors[0][i]],'next_neighbor':cs[neighbors[1][i]],
              'agrees':neighbors[0][i]==neighbors[1][i]} for i,c in enumerate(cs)])
    table(subset/'pairwise-distance-differences.csv',[{'constitution_a':cs[i],'constitution_b':cs[j],
             'first_A_distance':float(distances[0][i,j]),'next_A_distance':float(distances[1][i,j]),
             'absolute_difference':float(abs(distances[1][i,j]-distances[0][i,j]))} for i in range(len(cs)) for j in range(i+1,len(cs))])
    summary.update(run_id=manifest['run_id'],scope=f'DESCRIPTIVE_DISJOINT_{n}_VS_{n}_SCENARIOS',api_requests=0,full_experiment_complete=False,
                   interpretation='Granite-conditioned exploratory behavior; not established philosophical distances or proof of stable population geometry.')
    (subset/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--through-batch',type=int,required=True);a=p.parse_args()
    assert a.through_batch>=1  # Offline only; complete even-sized prefix required.
    print(json.dumps(analyze(a.through_batch),indent=2))
