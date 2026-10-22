"""Analyze only the isolated final Granite pilot; never dispatch inference."""
import csv,json,math,os
from pathlib import Path
import numpy as np
from scipy.stats import rankdata,spearmanr
from constitution_distance.core import digest,distance_matrix
from constitution_distance.pilot_metrics import factorial_cell,factorial_distances

B=Path('/workspace/work/granite-final-pilot');O=Path('results/granite-final-pilot');O.mkdir(parents=True,exist_ok=True)
CN=['canonical','labels_swapped','order_reversed','both_reversed']

def pure(x):
 if isinstance(x,np.ndarray):return pure(x.tolist())
 if isinstance(x,(np.integer,np.floating,np.bool_)):return pure(x.item())
 if isinstance(x,float) and not math.isfinite(x):return None
 if isinstance(x,dict):return {str(k):pure(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [pure(v) for v in x]
 return x

def js(name,x):(O/name).write_text(json.dumps(pure(x),indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def table(name,rows):
 if not rows:return
 with (O/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(pure(rows))
def matrix(name,m,rs,cols):
 with (O/name).open('w') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['constitution']+list(cols));w.writerows([[r]+pure(list(v)) for r,v in zip(rs,m)])
def corr(a,b,rank=False):
 a=np.asarray(a);b=np.asarray(b)
 if rank:a=rankdata(np.round(a,12));b=rankdata(np.round(b,12))
 return None if np.ptp(a)<1e-14 or np.ptp(b)<1e-14 else float(np.corrcoef(a,b)[0,1])

def main():
 design=json.load(open(os.environ.get('GRANITE_DESIGN_FILE',str(B/'design-v2.json'))));rid=digest(design);folder=B/rid
 records=[json.loads(l) for l in (folder/'responses.jsonl').read_text().splitlines()]
 if len(records)!=len(design['items']):raise ValueError('Incomplete final pilot; no complete-matrix inference allowed')
 cs=sorted({r['item']['constitution_id'] for r in records if r['item']['kind']=='main'});ss=sorted({r['item']['scenario_id'] for r in records if r['item']['kind']=='main'},key=int);ci={c:j for j,c in enumerate(cs)};si={s:j for j,s in enumerate(ss)}
 a=np.full((4,24,20,2),np.nan);baseline=np.full((4,20,2),np.nan);diag={};raw=[];source={}
 for r in records:
  i=r['item'];p=r['result'];key=(i['kind'],i['constitution_id'],i['scenario_id'],i['condition'],i['replica'])
  if key in source:raise ValueError('Duplicate slot')
  source[key]=r;k=CN.index(i['condition']);rep=i['replica']
  if i['kind']=='main':a[k,ci[i['constitution_id']],si[i['scenario_id']],rep]=p['p_to_do']
  elif i['kind']=='daily_baseline':baseline[k,si[i['scenario_id']],rep]=p['p_to_do']
  else:diag.setdefault((i['kind'],i['scenario_id'],i['constitution_id']),np.full((4,2),np.nan))[k,rep]=p['p_to_do']
  raw.append({'kind':i['kind'],'constitution':i['constitution_id'],'scenario':i['scenario_id'],'condition':i['condition'],'replica':rep,'p_to_do':p['p_to_do'],'p1_conditional':p['p1_conditional'],'logp0':p['logp0'],'logp1':p['logp1'],'p0_unconditional':p['p0'],'p1_unconditional':p['p1'],'binary_mass':p['binary_mass'],'log_odds1_over0':p['log_odds'],'request_hash':r['request_hash'],'prompt_hash':r['prompt_hash'],'wire_hash':r['response'].get('_transport',{}).get('request_body_sha256'),'response_id':r['response']['id'],'provider':r['response']['provider'],'model':r['response']['model'],'completed_at':r['completed_at'],'input_tokens':r['response']['usage']['prompt_tokens'],'output_tokens':r['response']['usage']['completion_tokens'],'cost':r['response']['usage']['cost']})
 assert not np.isnan(a).any() and not np.isnan(baseline).any() and all(not np.isnan(v).any() for v in diag.values())
 table('evaluations.csv',raw)
 p=a.mean(-1);base=baseline.mean(-1);computed=factorial_distances(p.tolist());cb=np.array(computed['counterbalanced_probabilities']);ds=np.array(computed['condition_sum_l1'])/20;dcb=np.array(computed['counterbalanced_sum_l1'])/20;avgd=ds.mean(0);names=CN+['counterbalanced'];allp=list(p)+[cb];alld=list(ds)+[dcb]
 for name,v,d in zip(names,allp,alld):
  matrix('probabilities-'+name+'.csv',v,cs,ss);matrix('distances-'+name+'-mean-l1.csv',d,cs,cs);matrix('distances-'+name+'-summed-l1.csv',d*20,cs,cs)
 cell=[];le=np.zeros((24,20));oe=le.copy();interaction=le.copy();ranges=le.copy()
 for c in cs:
  for s in ss:
   j=ci[c];z=si[s];f=factorial_cell(p[:,j,z].tolist());row={'constitution':c,'dilemma':s}
   for k,n in enumerate(CN):row.update({n+'_rep0':a[k,j,z,0],n+'_rep1':a[k,j,z,1],n+'_mean':p[k,j,z],n+'_repeat_difference':abs(a[k,j,z,0]-a[k,j,z,1])})
   row.update(f);cell.append(row);le[j,z]=f['label_effect'];oe[j,z]=f['order_effect'];interaction[j,z]=f['interaction'];ranges[j,z]=f['range']
 table('cell-statistics.csv',cell);table('no-constitution-baseline.csv',[{'dilemma':s,**{n:base[k,si[s]] for k,n in enumerate(CN)},'counterbalanced':base[:,si[s]].mean(),'max_repeat_difference':np.max(abs(baseline[:,si[s],0]-baseline[:,si[s],1]))} for s in ss])
 tr=np.triu_indices(24,1);comparisons=[]
 for i,j in zip(*tr):comparisons.append({'constitution_a':cs[i],'constitution_b':cs[j],'canonical_mean_l1':ds[0,i,j],'counterbalanced_mean_l1':dcb[i,j],'signed_difference':dcb[i,j]-ds[0,i,j],'absolute_difference':abs(dcb[i,j]-ds[0,i,j]),'canonical_summed_l1':ds[0,i,j]*20,'counterbalanced_summed_l1':dcb[i,j]*20,'average_four_distances_not_primary':avgd[i,j],'jensen_gap':avgd[i,j]-dcb[i,j]})
 table('distance-comparison.csv',comparisons)
 correlations={n:{m:{'pearson':corr(alld[i][tr],alld[j][tr]),'spearman':corr(alld[i][tr],alld[j][tr],True)} for j,m in enumerate(names)} for i,n in enumerate(names)}
 rankrows=[];neighbors=[]
 for i,c in enumerate(cs):
  others=np.array([j for j in range(24) if j!=i]);v=ds[0,i,others];w=dcb[i,others];vr=rankdata(np.round(v,12));wr=rankdata(np.round(w,12));vmin=set(others[v<=v.min()+1e-12]);wmin=set(others[w<=w.min()+1e-12]);v3=set(others[v<=np.sort(v)[2]+1e-12]);w3=set(others[w<=np.sort(w)[2]+1e-12])
  neighbors.append({'constitution':c,'canonical_nearest':';'.join(cs[j] for j in sorted(vmin)),'counterbalanced_nearest':';'.join(cs[j] for j in sorted(wmin)),'nearest_overlap':bool(vmin&wmin),'top3_jaccard_tie_aware':len(v3&w3)/len(v3|w3),'rank_spearman':corr(v,w,True),'canonical_unique_distances':len(set(np.round(v,12))),'counterbalanced_unique_distances':len(set(np.round(w,12)))})
  for j,x,y in zip(others,vr,wr):rankrows.append({'constitution':c,'neighbor':cs[j],'canonical_rank':x,'counterbalanced_rank':y,'rank_change':y-x,'canonical_mean_distance':ds[0,i,j],'counterbalanced_mean_distance':dcb[i,j]})
 table('neighbor-rankings.csv',rankrows);table('nearest-neighbor-comparison.csv',neighbors)
 rng=np.random.default_rng(20261022);ix=rng.integers(0,20,(5000,20))
 def effects(v):
  boot=v[:,ix].mean(axis=(0,2));return {'mean_signed':v.mean(),'mean_absolute':abs(v).mean(),'median_absolute':np.median(abs(v)),'maximum_absolute':abs(v).max(),'fraction_absolute_gt_0.05':np.mean(abs(v)>.05),'fraction_absolute_gt_0.10':np.mean(abs(v)>.1),'signed_mean_dilemma_cluster_bootstrap_95':np.quantile(boot,[.025,.975])}
 within=np.mean([abs(p[j]-p[k]).mean() for j in range(4) for k in range(j+1,4)]);between=float(ds[0][tr].mean());ratio=float(within/between) if between else None
 baselinechanges=[]
 for c in cs:baselinechanges.append({'constitution':c,'canonical_mean_absolute_shift_from_baseline':abs(p[0,ci[c]]-base[0]).mean(),'counterbalanced_mean_absolute_shift_from_baseline':abs(cb[ci[c]]-base.mean(0)).mean(),'canonical_signed_shift':np.mean(p[0,ci[c]]-base[0]),'counterbalanced_signed_shift':np.mean(cb[ci[c]]-base.mean(0))})
 table('constitution-baseline-shifts.csv',baselinechanges)
 daily=[]
 for s in ss:
  z=si[s];hi=int(np.argmax(cb[:,z]));lo=int(np.argmin(cb[:,z]));daily.append({'dilemma':s,'counterbalanced_spread':np.ptp(cb[:,z]),'canonical_spread':np.ptp(p[0,:,z]),'high_constitution':cs[hi],'high_p':cb[hi,z],'low_constitution':cs[lo],'low_p':cb[lo,z],'baseline_counterbalanced':base[:,z].mean(),'baseline_canonical':base[0,z]})
 daily.sort(key=lambda x:-x['counterbalanced_spread']);table('dilemma-contrasts.csv',daily)
 pred=design['preregistered_predictions'];diagrows=[];diagcontrasts=[]
 for case in pred['cases']:
  sid=case['id'];basevec=diag[('diagnostic_baseline',sid,'no-constitution')].mean(-1)
  for mode in ['full','excerpt','title_only']:
   vals={}
   for pp in case['predictions']:
    c=pp['constitution'];v=diag[('diagnostic_'+mode,sid,c)];vv=v.mean(-1);sgn=1 if pp['anticipated']=='high' else -1;vals[c]=float(vv.mean())
    diagrows.append({'diagnostic':sid,'mode':mode,'constitution':c,'anticipated':pp['anticipated'],'confidence':case['confidence'],**{n:vv[k] for k,n in enumerate(CN)},'counterbalanced':vv.mean(),'signed_margin_from_half':sgn*(vv.mean()-.5),'correct_direction':bool(sgn*(vv.mean()-.5)>1e-12),'conditions_supporting_direction':int(np.sum(sgn*(vv-.5)>1e-12)),'signed_shift_from_no_constitution':sgn*(vv.mean()-basevec.mean()),'baseline_counterbalanced':basevec.mean(),'max_repeat_difference':abs(v[:,0]-v[:,1]).max()})
   pp=case['predictions'];same=pp[0]['anticipated']==pp[1]['anticipated']
   if not same:
    high=next(x['constitution'] for x in pp if x['anticipated']=='high');low=next(x['constitution'] for x in pp if x['anticipated']=='low');gap=vals[high]-vals[low]
   else:high=low=None;gap=None
   diagcontrasts.append({'diagnostic':sid,'mode':mode,'confidence':case['confidence'],'comparison_type':'agreement' if same else 'contrast','high_constitution':high,'low_constitution':low,'expected_signed_gap':gap,'gap_correct':None if gap is None else gap>1e-12,'gap_ge_0.10':None if gap is None else gap>=.1,'automated_hypothesis_not_human_reviewed':True})
 table('diagnostic-prediction-results.csv',diagrows);table('diagnostic-contrast-results.csv',diagcontrasts)
 summary={'run_id':rid,'counts':{'valid_all':len(records),'main':int(a.size),'no_constitution_daily':int(baseline.size),'diagnostic':sum(v.size for v in diag.values())},'quality_checks':{'missing':0,'probabilities_in_range':bool(np.all((a>=0)&(a<=1))),'maximum_main_repeat_difference':np.max(abs(a[:,:,:,0]-a[:,:,:,1])),'maximum_baseline_repeat_difference':np.max(abs(baseline[:,:,0]-baseline[:,:,1])),'maximum_diagnostic_repeat_difference':max(np.max(abs(v[:,0]-v[:,1])) for v in diag.values()),'distance_symmetry':all(np.max(abs(d-d.T))<1e-12 for d in alld),'zero_diagonals':all(np.max(abs(np.diag(d)))<1e-12 for d in alld),'nonnegative_distances':all(np.min(d)>=0 for d in alld),'counterbalanced_not_average_distances':True,'maximum_jensen_gap':np.max(avgd-dcb)},'effects':{'label':effects(le),'order':effects(oe),'interaction':effects(interaction),'cell_condition_std_mean':np.mean(np.std(p,axis=0)),'cell_condition_range_mean':ranges.mean(),'cell_condition_range_max':ranges.max(),'mean_within_cell_between_condition_absolute_change':within,'mean_canonical_between_constitution_distance':between,'ratio_within_prompt_effect_to_between_constitution_distance':ratio,'exploratory_size_category':'undefined' if ratio is None else 'negligible' if ratio<.1 else 'moderate' if ratio<.5 else 'large','category_thresholds':'Exploratory heuristic:ratio<.1 negligible,.1–.5 moderate,>=.5 large; report continuous values.'},'distance_comparison':{'correlations':correlations,'canonical_mean':between,'counterbalanced_mean':dcb[tr].mean(),'canonical_range':[ds[0][tr].min(),ds[0][tr].max()],'counterbalanced_range':[dcb[tr].min(),dcb[tr].max()],'mean_absolute_change':np.mean(abs(ds[0][tr]-dcb[tr])),'maximum_absolute_change':np.max(abs(ds[0][tr]-dcb[tr])),'nearest_neighbor_overlap_constitutions':sum(n['nearest_overlap'] for n in neighbors),'mean_top3_jaccard_tie_aware':np.mean([n['top3_jaccard_tie_aware'] for n in neighbors])},'fidelity':{'full_prediction_correct':sum(r['correct_direction'] for r in diagrows if r['mode']=='full'),'prediction_count':12,'full_high_confidence_correct':sum(r['correct_direction'] for r in diagrows if r['mode']=='full' and not r['confidence'].startswith('interpretively')),'full_high_confidence_count':8,'mean_signed_normative_shift_from_baseline_full':np.mean([r['signed_shift_from_no_constitution'] for r in diagrows if r['mode']=='full']),'interpretation':'Assistant-generated hypotheses and posthoc DailyDilemmas interpretation, not human-reviewed truth; report all failures and ambiguities.'},'statistics_notes':'Correlations/rankings descriptive:276 constitution pairs not independent. Effects95%CIs resample20dilemma clusters, retaining24constitutions together;5000draws seed20261022. Fixed selected pilot, not population evidence. Ranks tie-rounded12decimals; probabilities/distances not rounded.'}
 js('statistical-summary.json',summary);js('analysis-plan-and-predictions.json',pred)
 # Full-cost extrapolation using matched pilot tokenization, not cache discounts.
 old=[json.loads(l) for l in Path('/workspace/work/controlled-v2/pilot/responses.jsonl').read_text().splitlines()];oldtokens=sum(r['response']['usage']['prompt_tokens'] for r in old)
 canonical=[r for r in raw if r['kind']=='main' and r['condition']=='canonical' and r['replica']==0];canonical_tokens=sum(r['input_tokens'] for r in canonical);ratio_tokens=canonical_tokens/oldtokens
 proj={}
 for n in [1336,1360]:
  logical=24*n;inp=96464288*n/1336*ratio_tokens;single=inp*.017/1e6+logical*.112/1e6
  proj[str(n)]={'logical_constitution_scenario_pairs':logical,'canonical_calls_r1':logical,'canonical_cost_r1':single,'counterbalanced_calls_r1':4*logical,'counterbalanced_cost_r1':single*4,'counterbalanced_calls_r2':8*logical,'counterbalanced_cost_r2':single*8}
 js('full-cost-projection.json',{'estimates':proj,'matched_tokenization_ratio':ratio_tokens,'not_authorization':True,'uncertainty':'Approx±20% token extrapolation; excludes canaries,retries,pricechanges;held-outscenario approval unchanged.'})
 plots(p,cb,ds,dcb,le,oe,ranges,diagrows,cs,ss)
 print(json.dumps(pure(summary),indent=2))

def plots(p,cb,ds,dcb,le,oe,ranges,diagrows,cs,ss):
 os.environ.setdefault('MPLCONFIGDIR','/workspace/work/granite-final-pilot/mpl-cache')
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 labels=[x.replace('-',' ') for x in cs]
 def save(fig,name):fig.savefig(O/(name+'.png'),dpi=170,bbox_inches='tight');fig.savefig(O/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
 fig,axes=plt.subplots(1,5,figsize=(25,10),sharey=True)
 for ax,m,name in zip(axes,list(p)+[cb],CN+['counterbalanced']):
  im=ax.imshow(m,vmin=0,vmax=1,cmap='viridis',aspect='auto');ax.set_title(name.replace('_',' '));ax.set_xticks(range(20));ax.set_xticklabels(ss,rotation=90,fontsize=7)
 axes[0].set_yticks(range(24));axes[0].set_yticklabels(labels,fontsize=8);fig.colorbar(im,ax=axes.ravel().tolist(),label='P(original to_do action)',shrink=.6);save(fig,'probability-heatmaps')
 fig,axes=plt.subplots(1,5,figsize=(27,9));vmax=max(d.max() for d in list(ds)+[dcb])
 for ax,d,name in zip(axes,list(ds)+[dcb],CN+['counterbalanced']):
  im=ax.imshow(d,vmin=0,vmax=vmax,cmap='magma');ax.set_title(name.replace('_',' '));ax.set_xticks(range(24));ax.set_xticklabels(labels,rotation=90,fontsize=5);ax.set_yticks(range(24));ax.set_yticklabels(labels,fontsize=5)
 fig.colorbar(im,ax=axes.ravel().tolist(),label='Mean absolute behavioral distance',shrink=.6);save(fig,'distance-heatmaps')
 fig,axes=plt.subplots(1,3,figsize=(19,9),sharey=True)
 for ax,m,title in zip(axes,[le,oe,ranges],['Label effect','Action-order effect','Four-condition probability range']):
  im=ax.imshow(m,vmin=-1 if 'effect' in title else 0,vmax=1,cmap='coolwarm' if 'effect' in title else 'viridis',aspect='auto');ax.set_title(title);ax.set_xticks(range(20));ax.set_xticklabels(ss,rotation=90,fontsize=7);fig.colorbar(im,ax=ax,shrink=.5)
 axes[0].set_yticks(range(24));axes[0].set_yticklabels(labels,fontsize=8);save(fig,'prompt-sensitivity-heatmaps')
 tr=np.triu_indices(24,1);fig,ax=plt.subplots(figsize=(7,7));ax.scatter(ds[0][tr],dcb[tr],s=14,alpha=.6);lim=max(ds[0].max(),dcb.max())*1.05;ax.plot([0,lim],[0,lim],color='gray',linestyle='--');ax.set(xlabel='Canonical mean L1',ylabel='Counterbalanced mean L1',title='Distances between averaged probabilities',xlim=(0,lim),ylim=(0,lim));save(fig,'canonical-counterbalanced-scatter')
 fig,axes=plt.subplots(2,3,figsize=(18,10));cases=list(dict.fromkeys(r['diagnostic'] for r in diagrows))
 for ax,sid in zip(axes.flat,cases):
  rows=[r for r in diagrows if r['diagnostic']==sid];cc=list(dict.fromkeys(r['constitution'] for r in rows));x=np.arange(2)
  for j,mode in enumerate(['full','excerpt','title_only']):ax.bar(x+(j-1)*.23,[next(r['counterbalanced'] for r in rows if r['mode']==mode and r['constitution']==c) for c in cc],width=.23,label=mode)
  ax.axhline(.5,color='gray',linestyle=':');ax.axhline(rows[0]['baseline_counterbalanced'],color='black',linestyle='--',label='no constitution');ax.set_ylim(0,1);ax.set_xticks(x);ax.set_xticklabels([c.replace('-',' ') for c in cc],fontsize=8);ax.set_title(sid);ax.set_ylabel('Counterbalanced P(to_do)')
 axes[0,0].legend(fontsize=8);fig.tight_layout();save(fig,'diagnostic-fidelity-controls')

if __name__=='__main__':main()
