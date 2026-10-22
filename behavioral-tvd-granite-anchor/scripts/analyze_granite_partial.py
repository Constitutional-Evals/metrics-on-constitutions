"""Audit a stopped pilot without imputing missing probabilities or complete distances."""
import json,csv,math,os
from pathlib import Path
import numpy as np
from constitution_distance.core import digest
B=Path('/workspace/work/granite-final-pilot');O=Path(os.environ.get('GRANITE_PARTIAL_OUTPUT','results/granite-final-pilot-partial'));O.mkdir(parents=True,exist_ok=True)
D=json.load(open(os.environ.get('GRANITE_DESIGN_FILE',str(B/'design-v2.json'))));rid=digest(D);rs=[json.loads(l) for l in (B/rid/'responses.jsonl').read_text().splitlines()]
cs=sorted({i['constitution_id'] for i in D['items'] if i['kind']=='main'});ss=sorted({i['scenario_id'] for i in D['items'] if i['kind']=='main'},key=int);cn=['canonical','labels_swapped','order_reversed','both_reversed'];a=np.full((4,24,20,2),np.nan);groups={};kindcounts={}
for r in rs:
 i=r['item'];kindcounts[i['kind']]=kindcounts.get(i['kind'],0)+1;groups.setdefault((i['kind'],i['constitution_id'],i['scenario_id'],i['condition']),[]).append(r)
 if i['kind']=='main':a[cn.index(i['condition']),cs.index(i['constitution_id']),ss.index(i['scenario_id']),i['replica']]=r['result']['p_to_do']
n=np.isfinite(a).sum(-1);p=np.full((4,24,20),np.nan)
for idx in np.ndindex(p.shape):
 v=a[idx];p[idx]=v[np.isfinite(v)].mean() if np.isfinite(v).any() else np.nan
complete=np.all(np.isfinite(p),axis=0);cb=np.full((24,20),np.nan);cb[complete]=p[:,complete].mean(0);fullr2=np.all(n==2,axis=0);rows=[]
for c,cid in enumerate(cs):
 for s,sid in enumerate(ss):
  row={'constitution':cid,'dilemma':sid}
  for k,name in enumerate(cn):row.update({name+'_rep0':a[k,c,s,0],name+'_rep1':a[k,c,s,1],name+'_valid_repeats':int(n[k,c,s]),name+'_available_mean_NOT_FINAL':p[k,c,s]})
  row.update({'four_conditions_observed':bool(complete[c,s]),'all_eight_requests_valid':bool(fullr2[c,s]),'counterbalanced_available_NOT_FINAL':cb[c,s],'range_four_conditions':np.ptp(p[:,c,s]) if complete[c,s] else np.nan,'std_four_conditions':np.std(p[:,c,s]) if complete[c,s] else np.nan});rows.append(row)
def clean(x):
 if isinstance(x,(np.integer,np.floating,np.bool_)):return clean(x.item())
 if isinstance(x,float) and not math.isfinite(x):return None
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple,np.ndarray)):return [clean(v) for v in x]
 return x
def matrix(name,v,cols):
 with (O/name).open('w') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['constitution']+cols);w.writerows([[c]+clean(vv) for c,vv in zip(cs,v)])
with (O/'partial-cell-statistics.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(clean(rows))
for k,name in enumerate(cn):
 matrix('probabilities-'+name+'-available-NOT-FINAL.csv',p[k],ss);matrix('probabilities-'+name+'-strict-R2.csv',np.where(n[k]==2,p[k],np.nan),ss)
 # Every full20scenario distance is unavailable until both vectors cover all20.
 dist=np.full((24,24),np.nan)
 for i in range(24):
  for j in range(24):
   if np.isfinite(p[k,i]).all() and np.isfinite(p[k,j]).all():dist[i,j]=np.abs(p[k,i]-p[k,j]).sum()
 matrix('distances-'+name+'-summed-L1-NOT-FINAL.csv',dist,cs);matrix('distances-'+name+'-mean-L1-NOT-FINAL.csv',dist/20,cs)
matrix('probabilities-counterbalanced-available-NOT-FINAL.csv',cb,ss)
dcb=np.full((24,24),np.nan)
for i in range(24):
 for j in range(24):
  if np.isfinite(cb[i]).all() and np.isfinite(cb[j]).all():dcb[i,j]=np.abs(cb[i]-cb[j]).sum()
matrix('distances-counterbalanced-summed-L1-NOT-FINAL.csv',dcb,cs);matrix('distances-counterbalanced-mean-L1-NOT-FINAL.csv',dcb/20,cs)
repeatdiff=[abs(v[0]['result']['p_to_do']-v[1]['result']['p_to_do']) for v in groups.values() if len(v)==2];effect={}
if complete.any():
 q=p[:,complete];le=(q[1]+q[3]-q[0]-q[2])/2;oe=(q[2]+q[3]-q[0]-q[1])/2
 effect={'complete_four_condition_cells_any_replicates':int(complete.sum()),'mean_absolute_label_effect_available_cells':np.abs(le).mean(),'mean_absolute_order_effect_available_cells':np.abs(oe).mean(),'maximum_condition_probability_range_available_cells':np.ptp(q,axis=0).max(),'mean_condition_probability_range_available_cells':np.ptp(q,axis=0).mean(),'warning':'Exploratory incomplete subset, varying1–2replicates; not final factorial study or full-population estimate.'}
summary={'status':'STOPPED_ON_MISSING_LOGPROB_RESPONSE','run_id':rid,'valid_records':len(rs),'by_kind':kindcounts,'main_expected':3840,'main_valid':kindcounts.get('main',0),'main_missing':3840-kindcounts.get('main',0),'all_expected':4336,'all_missing':4336-len(rs),'identical_repeat_groups_observed':len(repeatdiff),'maximum_observed_repeat_difference':max(repeatdiff,default=None),'full_R2_four_condition_cells':int(fullr2.sum()),'partial_effects':effect,'distance_correlations_and_rankings':'NOT_ESTIMABLE_AS_REQUESTED_FROM_INCOMPLETE_MATRICES','all_matrix_NAs_explicit':True,'no_missing_probability_substituted':True,'prediction_files_frozen_before_inference':True}
(O/'partial-statistics.json').write_text(json.dumps(clean(summary),indent=2,allow_nan=False)+'\n');print(json.dumps(clean(summary),indent=2))
import os
os.environ.setdefault('MPLCONFIGDIR','/workspace/work/granite-final-pilot/mpl-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,5,figsize=(24,9),sharey=True);cmap=plt.colormaps['viridis'].copy();cmap.set_bad('#cccccc')
for ax,v,title in zip(axes,list(p)+[cb],cn+['counterbalanced']):
 im=ax.imshow(np.ma.masked_invalid(v),vmin=0,vmax=1,cmap=cmap,aspect='auto');ax.set_title(title+'\nINCOMPLETE');ax.set_xticks(range(20));ax.set_xticklabels(ss,rotation=90,fontsize=6)
axes[0].set_yticks(range(24));axes[0].set_yticklabels(cs,fontsize=7);fig.colorbar(im,ax=axes.ravel().tolist(),label='Available-replicate mean P(to_do); gray=missing',shrink=.6);fig.savefig(O/'partial-probability-heatmaps.png',dpi=160,bbox_inches='tight');fig.savefig(O/'partial-probability-heatmaps.pdf',bbox_inches='tight');plt.close(fig)
