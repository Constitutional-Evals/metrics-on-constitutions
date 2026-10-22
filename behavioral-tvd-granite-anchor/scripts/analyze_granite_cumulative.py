"""Offline, preliminary prefix analyses; never dispatches inference.

Reconstructs each prefix from individual semantic probabilities, then calculates
A/B/C afresh. Independent scalar loops verify every exported matrix entry.
"""
import argparse
import gzip
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from analyze_granite_exploratory import matrix, table
from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE, CONDITIONS, verify_manifest
from final_granite_pilot import validate


def analyze(through):
    m = json.loads(Path('configs/granite-exploratory-approved.json').read_text())
    verify_manifest(m)
    assert 1<=through<=len(m['batches'])
    cs = m['constitution_order']
    ids = [s for b in m['batches'][:through] for s in b['scenario_ids']]
    si, ci = {s:j for j,s in enumerate(ids)}, {c:j for j,c in enumerate(cs)}
    p = np.full((4,24,len(ids)),np.nan)
    baseline = np.full((4,len(ids)),np.nan)
    seen = set()
    for b in range(1,through+1):
        for r in map(json.loads,gzip.open(f'results/granite-exploratory/batch-{b:04d}/responses.jsonl.gz','rt')):
            if r['item']['kind']=='canary': continue
            pair = tuple(r['item']['pair']); c,s,k = pair
            assert pair not in seen; seen.add(pair)
            assert r['request_hash']==digest(r['request'])
            assert r['prompt_hash']==digest(r['request']['messages'])
            assert r['result']==validate(r['item'],r['response'])
            if c==BASELINE: baseline[k,si[s]]=r['result']['p_to_do']
            else: p[k,ci[c],si[s]]=r['result']['p_to_do']
    assert len(seen)==len(ids)*100 and np.isfinite(p).all() and np.isfinite(baseline).all()
    assert ((p>=0)&(p<=1)).all() and ((baseline>=0)&(baseline<=1)).all()
    out = Path(f'results/granite-exploratory/cumulative-through-{through:04d}')
    out.mkdir(parents=True,exist_ok=True)
    tri=np.triu_indices(24,1); evolution=[]; rankings=[]; previous={}; last={}; max_error=0.
    for b in range(1,through+1):
        n=sum(len(x['scenario_ids']) for x in m['batches'][:b]); v=p[:,:,:n]; q=v.mean(0)
        sums={'A_primary':abs(q[:,None,:]-q[None,:,:]).sum(-1),
              'B_secondary':abs(v[:,:,None,:]-v[:,None,:,:]).sum(-1).mean(0),
              'C_canonical':abs(v[0,:,None,:]-v[0,None,:,:]).sum(-1)}
        assert np.all(sums['A_primary']<=sums['B_secondary']+1e-12)
        for name,d in sums.items():
            assert np.array_equal(d,d.T) and np.all(d.diagonal()==0) and (d>=0).all()
            for i in range(24):
                for j in range(24):
                    if name=='A_primary': ref=math.fsum(abs(math.fsum(v[k,i,s] for k in range(4))/4-math.fsum(v[k,j,s] for k in range(4))/4) for s in range(n))
                    elif name=='B_secondary': ref=math.fsum(abs(v[k,i,s]-v[k,j,s]) for k in range(4) for s in range(n))/4
                    else: ref=math.fsum(abs(v[0,i,s]-v[0,j,s]) for s in range(n))
                    max_error=max(max_error,abs(ref-d[i,j])); assert abs(ref-d[i,j])<1e-12
            neighbors=[min((j for j in range(24) if j!=i),key=lambda j:(d[i,j],cs[j])) for i in range(24)]
            entry={'through_batch':b,'scenarios':n,'metric':name,'mean_normalized_distance':float(d[tri].mean()/n),
                   'minimum_normalized_distance':float(d[tri].min()/n),'maximum_normalized_distance':float(d[tri].max()/n),
                   'spearman_previous_prefix':None,'nearest_neighbors_unchanged_from_previous':None}
            if name in previous:
                old,old_neighbors=previous[name]
                entry.update(spearman_previous_prefix=float(spearmanr(old,d[tri]/n).statistic),
                             nearest_neighbors_unchanged_from_previous=sum(a==b for a,b in zip(neighbors,old_neighbors)))
            previous[name]=(d[tri]/n,neighbors); evolution.append(entry)
            matrix(out/f'prefix-{n:04d}-distances-{name}-normalized-l1.csv',d/n,cs,cs)
            for i,c in enumerate(cs):
                for rank,j in enumerate(sorted((j for j in range(24) if j!=i),key=lambda j:(d[i,j],cs[j])),1):
                    rankings.append({'scenarios':n,'metric':name,'constitution':c,'neighbor':cs[j],'rank_with_id_tiebreak':rank,'normalized_distance':d[i,j]/n})
        last=sums
    n=len(ids); q=p.mean(0)
    matrix(out/'probabilities-counterbalanced.csv',q,cs,ids)
    for k,(name,_,_) in enumerate(CONDITIONS):matrix(out/f'probabilities-{name}.csv',p[k],cs,ids)
    for name,d in last.items():
        matrix(out/f'distances-{name}-summed-l1.csv',d,cs,cs)
        matrix(out/f'distances-{name}-normalized-l1.csv',d/n,cs,cs)
    table(out/'baseline.csv',[{'scenario':s,**{CONDITIONS[k][0]:baseline[k,j] for k in range(4)},'counterbalanced':float(baseline[:,j].mean())} for j,s in enumerate(ids)])
    table(out/'baseline-shifts.csv',[{'constitution':c,'mean_absolute_shift':float(abs(q[i]-baseline.mean(0)).mean()),'mean_signed_shift':float((q[i]-baseline.mean(0)).mean())} for i,c in enumerate(cs)])
    table(out/'geometry-evolution.csv',evolution); table(out/'similarity-rankings-evolution.csv',rankings)
    rng=np.random.default_rng(20261022); sampling=[]
    for size in sorted({max(2,n//4),max(2,n//2)}):
        rhos=[]; errors=[]
        for _ in range(100):
            ix=rng.choice(n,size,replace=False); sub=q[:,ix]
            d=abs(sub[:,None,:]-sub[None,:,:]).mean(-1)[tri]; ref=last['A_primary'][tri]/n
            rhos.append(float(spearmanr(d,ref).statistic)); errors.append(float(abs(d-ref).mean()))
        sampling.append({'sample_size':size,'draws':100,'mean_spearman':float(np.mean(rhos)), 'spearman_p05':float(np.quantile(rhos,.05)), 'spearman_p95':float(np.quantile(rhos,.95)),'mean_absolute_distance_error':float(np.mean(errors))})
    table(out/'scenario-subsampling.csv',sampling)
    summary={'run_id':digest(m),'scope':f'PRELIMINARY_FIRST_{n}_SCENARIOS','full_experiment_complete':False,
             'scenario_ids':ids,'primary_evaluations':p.size,'baseline_evaluations':baseline.size,'missing':0,
             'matrix_shape':[24,n],'api_requests':0,'maximum_independent_scalar_verification_error':max_error,
             'probabilities_in_range':True,'symmetry_zero_diagonal_nonnegative':True,'A_not_B':True,
             'computation':'Reconstructed individual semantic probabilities over pooled prefix scenarios; A uses four-condition mean vectors; B averages condition-specific distances; C canonical. Normalized=sum/N.',
             'interpretation':'Preliminary Granite-conditioned geometry; neither final 1336-scenario results nor established philosophical distances.',
             'evolution':evolution,'subsampling_seed':20261022,'subsampling':sampling}
    (out/'analysis-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--through-batch',type=int,required=True)
    a=parser.parse_args(); assert a.through_batch>=1
    print(json.dumps(analyze(a.through_batch),indent=2))
