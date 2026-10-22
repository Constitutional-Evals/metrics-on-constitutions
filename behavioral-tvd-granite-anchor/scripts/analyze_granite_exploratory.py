"""Offline batch analysis, or full exports only after the entire grid completes."""
import argparse
import csv
import fcntl
import gzip
import json
from pathlib import Path
import sqlite3

import numpy as np
from scipy.stats import spearmanr
from constitution_distance.core import digest
from constitution_distance.exploratory import BASELINE, CANARY, CONDITIONS, verify_manifest
from constitution_distance.local import file_hash
from constitution_distance.pilot_metrics import factorial_distances
from final_granite_pilot import validate


def matrix(path, values, rows, columns):
    with path.open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['constitution']+list(columns))
        w.writerows([[label]+list(row) for label,row in zip(rows,values)])


def table(path, rows):
    if not rows:return
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def full_completion_check(db, run_id, required_pairs):
    """Scientific completeness and conservative accounting are separate checks.

    Settled unknown-cost failures remain charged and disclosed, including when a
    successful retry completed their logical evaluation. This function is RO.
    """
    attempts=db.execute('SELECT state,reserve,charged,actual_cost,finished FROM attempts WHERE run=?',(run_id,)).fetchall()
    if any(a[0]=='reserved' for a in attempts):
        raise ValueError('Outstanding reserved requests; full completion refused')
    states={(c,s,k):state for c,s,k,state in db.execute('SELECT cid,sid,replica,state FROM evaluations WHERE run=?',(run_id,))}
    if any(state!='valid' for state in states.values()) or any(states.get(tuple(p))!='valid' for p in required_pairs):
        raise ValueError('Missing/invalid science or required canaries; full completion refused')
    unknown=[a for a in attempts if a[3] is None]
    if any(a[4] is None or a[2]<a[1] for a in unknown):
        raise ValueError('Unsettled or under-accounted unknown billing; full completion refused')
    return {'settled_unknown_billing_attempts':len(unknown),
            'conservative_unknown_billing_charges_usd':sum(a[2] for a in unknown)/1e9,
            'unknown_external_costs_disclosed_not_imputed':True}


def analyze(m, root, out, batch=None):
    verify_manifest(m)
    cs=m['constitution_order'];ids=[s['id'] for s in m['scenarios']] if batch is None else m['batches'][batch-1]['scenario_ids']
    si={s:j for j,s in enumerate(ids)};ci={c:j for j,c in enumerate(cs)};n=len(ids)
    p=np.full((4,24,n),np.nan);baseline=np.full((4,n),np.nan);seen=set();raw=[]
    with (root/'.experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        db=sqlite3.connect(f'file:{root}/ledger.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:
            qc_sql="SELECT COUNT(*) FROM evaluations WHERE run=? AND cid=? AND state!='valid'"
            qc_params=[digest(m),CANARY]
            if batch is not None:qc_sql+=' AND sid LIKE ?';qc_params.append(f'b{batch:04d}-%')
            if db.execute(qc_sql,qc_params).fetchone()[0]:
                raise ValueError('Canary schedule incomplete or failed; complete-matrix export refused')
            billing_disclosure=None
            if batch is None:
                with gzip.open('data/granite-exploratory/task-plan.jsonl.gz','rt') as plan:
                    billing_disclosure=full_completion_check(db,digest(m),(json.loads(line)['pair'] for line in plan))
            sql="SELECT record FROM evaluations WHERE run=? AND state='valid' AND cid!=?"
            params=[digest(m),CANARY]
            if batch is not None:
                sql+=' AND sid IN ('+','.join('?' for _ in ids)+')';params+=ids
            for row in db.execute(sql,params):
                r=json.loads(row['record']);i=r['item'];pair=tuple(i['pair']);cid,sid,k=pair
                if pair in seen:raise ValueError('Duplicate evaluation')
                seen.add(pair)
                if r['request_hash']!=digest(r['request']) or r['prompt_hash']!=digest(r['request']['messages']) or r['result']!=validate(i,r['response']):
                    raise ValueError('Stored request/distribution integrity failure')
                q=r['result'];u=r['response']['usage']
                if cid==BASELINE:baseline[k,si[sid]]=q['p_to_do']
                else:p[k,ci[cid],si[sid]]=q['p_to_do']
                raw.append({'constitution':cid,'scenario':sid,'condition':CONDITIONS[k][0],
                    **{z:q[z] for z in ['p_to_do','logp0','logp1','log_odds','p0','p1','binary_mass','p1_conditional','sampled_output','format_compliant']},
                    'request_hash':r['request_hash'],'prompt_hash':r['prompt_hash'],'model':r['response']['model'],
                    'provider':r['response']['provider'],'response_id':r['response']['id'],
                    **{z:u[z] for z in ['prompt_tokens','completion_tokens','cost']}})
            assert len(seen)==25*n*4 and np.isfinite(p).all() and np.isfinite(baseline).all(), 'Incomplete grid: no complete matrices or imputation permitted'
            expected={}
            for line in gzip.open('data/granite-exploratory/task-plan.jsonl.gz','rt'):
                i=json.loads(line)
                if (batch is None or i['batch']==batch) and i['kind']!='canary':expected[tuple(i['pair'])]=i['request_hash']
            for row in raw:
                key=(row['constitution'],row['scenario'],[x[0] for x in CONDITIONS].index(row['condition']))
                assert row['request_hash']==expected[key]
        finally:db.close()
    out.mkdir(parents=True,exist_ok=True)
    f=factorial_distances(p.tolist());q=np.asarray(f['counterbalanced_probabilities'])
    ds=np.asarray(f['condition_sum_l1']);summed={'A_primary':np.asarray(f['counterbalanced_sum_l1']),
        'B_secondary':np.asarray(f['average_condition_distance_not_primary']),'C_canonical':ds[0]}
    assert np.all((p>=0)&(p<=1)) and np.all((baseline>=0)&(baseline<=1))
    for name,value in summed.items():
        assert np.allclose(value,value.T,atol=1e-12) and np.all(np.diag(value)==0) and np.min(value)>=0
        matrix(out/('distances-'+name+'-summed-l1.csv'),value,cs,cs)
        matrix(out/('distances-'+name+'-normalized-l1.csv'),value/n,cs,cs)
    assert np.all(summed['A_primary']<=summed['B_secondary']+1e-12)
    for k,(name,_,_) in enumerate(CONDITIONS):matrix(out/('probabilities-'+name+'.csv'),p[k],cs,ids)
    matrix(out/'probabilities-counterbalanced.csv',q,cs,ids)
    table(out/'evaluations.csv',raw)
    base=baseline.mean(0)
    table(out/'baseline.csv',[{'scenario':sid,**{CONDITIONS[k][0]:baseline[k,j] for k in range(4)},'counterbalanced':base[j]} for j,sid in enumerate(ids)])
    table(out/'baseline-shifts.csv',[{'constitution':cid,'counterbalanced_mean_absolute_shift':float(abs(q[i]-base).mean()),
        'counterbalanced_mean_signed_shift':float((q[i]-base).mean()),'canonical_mean_absolute_shift':float(abs(p[0,i]-baseline[0]).mean())} for i,cid in enumerate(cs)])
    labels=(p[1]+p[3]-p[0]-p[2])/2;order=(p[2]+p[3]-p[0]-p[1])/2
    table(out/'prompt-sensitivity.csv',[{'constitution':cid,'scenario':sid,'label_effect':labels[i,j],
        'action_line_order_effect':order[i,j],'four_condition_range':np.ptp(p[:,i,j]),'four_condition_std':np.std(p[:,i,j])}
        for i,cid in enumerate(cs) for j,sid in enumerate(ids)])
    tri=np.triu_indices(24,1);rank=[];contributions=[]
    for name,mat in summed.items():
        for i,cid in enumerate(cs):
            neighbors=sorted((j for j in range(24) if j!=i),key=lambda j:(mat[i,j],cs[j]))
            rank += [{'metric':name,'constitution':cid,'neighbor':cs[j],'rank_with_id_tiebreak':r+1,'normalized_distance':mat[i,j]/n} for r,j in enumerate(neighbors)]
    table(out/'similarity-rankings.csv',rank)
    for i,j in zip(*tri):
        for s,sid in enumerate(ids):
            a=abs(q[i,s]-q[j,s]);b=abs(p[:,i,s]-p[:,j,s]).mean();c=abs(p[0,i,s]-p[0,j,s])
            contributions.append({'constitution_a':cs[i],'constitution_b':cs[j],'scenario':sid,
                'A_summed_contribution':a,'B_summed_contribution':b,'C_summed_contribution':c,
                'A_normalized_contribution':a/n,'B_normalized_contribution':b/n,'C_normalized_contribution':c/n})
    table(out/'scenario-contributions.csv',contributions)
    rng=np.random.default_rng(20261022);sampling=[];reference=summed['A_primary'][tri]/n
    for size in sorted({max(2,n//4),max(2,n//2)}):
        correlations=[];errors=[]
        for _ in range(100):
            ix=rng.choice(n,size,replace=False);v=q[:,ix];d=np.abs(v[:,None,:]-v[None,:,:]).mean(-1)[tri]
            correlations.append(float(spearmanr(reference,d).statistic));errors.append(float(abs(d-reference).mean()))
        sampling.append({'sample_size':size,'draws':100,'mean_spearman':float(np.mean(correlations)),
            'spearman_p05':float(np.quantile(correlations,.05)),'spearman_p95':float(np.quantile(correlations,.95)),
            'mean_absolute_distance_error':float(np.mean(errors)),'warning':'Within analyzed scenario set only; descriptive, not population assurance.'})
    table(out/'scenario-subsampling.csv',sampling)
    summary={'run_id':digest(m),'analysis_source_sha256':file_hash(__file__),'scope':'FULL_COMPLETE_EXPERIMENT' if batch is None else f'BATCH_{batch}_ONLY',
      'interpretation':'Granite-conditioned prompt-induced behavior, not philosophical distances or fidelity certification.',
      'constitutions':24,'scenarios':n,'primary_evaluations':int(p.size),'baseline_evaluations':int(baseline.size),'missing':0,
      'all_request_hashes_match_frozen_plan':True,'probabilities_in_range':True,'symmetry_zero_diagonal_nonnegative':True,
      'A_not_B':True,'maximum_normalized_jensen_gap':float((summed['B_secondary']-summed['A_primary']).max()/n),
      'mean_pair_distances':{name:float(mat[tri].mean()/n) for name,mat in summed.items()},
      'A_C_spearman':float(spearmanr(summed['A_primary'][tri],summed['C_canonical'][tri]).statistic),
      'mean_absolute_label_effect':float(abs(labels).mean()),'mean_absolute_order_effect':float(abs(order).mean()),
      'mean_four_condition_range':float(np.ptp(p,axis=0).mean()),'minimum_binary_mass':min(r['binary_mass'] for r in raw),
      'format_noncompliant':sum(not r['format_compliant'] for r in raw),
      'fraction_log_odds_on_0.125_grid_abs_tolerance1e-5':float(np.mean([abs(r['log_odds']-.125*round(r['log_odds']/.125))<1e-5 for r in raw])),
      'numerical_limitation':'Previouslyobserved0.125log-oddsquantization; retained as a limitation.',
      'subsampling_seed':20261022,'full_experiment_complete':batch is None}
    if billing_disclosure is not None:summary['billing_disclosure']=billing_disclosure
    (out/'analysis-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    import os
    os.environ.setdefault('MPLCONFIGDIR','/workspace/work/granite-exploratory-mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(23,9),sharey=True);vmax=max(mat.max()/n for mat in summed.values())
    for j,(ax,(name,mat)) in enumerate(zip(axes,summed.items())):
        im=ax.imshow(mat/n,vmin=0,vmax=vmax,cmap='magma');ax.set_title(name);ax.set_xticks(range(24));ax.set_xticklabels(cs,rotation=90,fontsize=6);ax.set_yticks(range(24));ax.set_yticklabels(cs,fontsize=6);ax.tick_params(axis='y',labelleft=j==0)
    fig.colorbar(im,ax=axes.tolist(),label='Normalized L1 (batch scope)' if batch else 'Normalized L1',shrink=.6)
    for ext in ['png','pdf']:fig.savefig(out/('distance-heatmaps.'+ext),dpi=160,bbox_inches='tight')
    plt.close(fig)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--batch',type=int);g.add_argument('--full',action='store_true');a=p.parse_args()
    m=json.loads(Path('configs/granite-exploratory-approved.json').read_text());rid=digest(m)
    root=Path('/workspace/work/granite-exploratory')/rid
    out=Path('results/granite-exploratory')/('full' if a.full else f'batch-{a.batch:04d}')
    print(json.dumps(analyze(m,root,out,a.batch),indent=2))
