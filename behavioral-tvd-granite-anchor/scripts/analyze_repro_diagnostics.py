"""Regenerate diagnostic summaries from isolated raw study outputs; never sends requests."""
import csv,hashlib,json,math,sqlite3,statistics
from collections import defaultdict
from pathlib import Path
BASE=Path('/workspace/work/repro-diagnostics-2026-10-20')
OUT=Path('results/repro-diagnostics');OUT.mkdir(parents=True,exist_ok=True)
rows=[];groups=defaultdict(list)
for f in sorted(BASE.glob('*/responses.jsonl')):
 for line in f.read_text().splitlines():
  r=json.loads(line);i=r['item'];a=r['response'];p=r['result']['probabilities'];phase=i.get('recovery_of',f.parent.name)
  row={'phase':phase,'recovered':bool(i.get('recovery_of')),'pair':i['constitution_id']+'--'+i['scenario_id'],'replica':i['replica'],'seed':r['request'].get('seed'),'provider':a['provider'],'model':a['model'],'id':a['id'],'created':a.get('created'),'completed_at':r['completed_at'],'request_hash':r['request_hash'],'prompt_hash':r['prompt_hash'],'wire_hash':a.get('_transport',{}).get('request_body_sha256'),'fingerprint':a.get('system_fingerprint'),'sampled':a['choices'][0]['message']['content'],'logp0':p['logp0'],'logp1':p['logp1'],'log_odds':p['logp1']-p['logp0'],'p':p['p1_conditional'],'binary_mass':p['binary_mass'],'input_tokens':a['usage']['prompt_tokens'],'output_tokens':a['usage']['completion_tokens'],'cached_tokens':a['usage'].get('prompt_tokens_details',{}).get('cached_tokens'),'cost':a['usage']['cost']}
  rows.append(row);groups[(phase,row['pair'],i['seeded'])].append(row)
with (OUT/'evaluations.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
groupstats=[]
for (phase,pair,seeded),rs in groups.items():
 ps=[r['p'] for r in rs];ls=[r['log_odds'] for r in rs]
 groupstats.append(dict(phase=phase,pair=pair,seeded=seeded,n=len(rs),mean_p=statistics.mean(ps),min_p=min(ps),max_p=max(ps),range_p=max(ps)-min(ps),sd_p=statistics.stdev(ps) if len(ps)>1 else None,range_log_odds=max(ls)-min(ls),unique_p=len(set(ps))))
with (OUT/'repeat-groups.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(groupstats[0]),lineterminator="\n");w.writeheader();w.writerows(groupstats)
summary={}
for phase in sorted({r['phase'] for r in rows}):
 rs=[r for r in rows if r['phase']==phase];gs=[g for g in groupstats if g['phase']==phase]
 summary[phase]={'valid':len(rs),'groups':len(gs),'max_range':max(g['range_p'] for g in gs),'median_range':statistics.median(g['range_p'] for g in gs),'nonidentical_groups':sum(g['unique_p']>1 for g in gs),'saturated':sum(min(r['p'],1-r['p'])<=.001 for r in rs),'cost':sum(r['cost'] for r in rs)}
# Independent original-pilot verification.
pilot=[json.loads(l) for l in Path('/workspace/work/controlled-v2/pilot/responses.jsonl').read_text().splitlines()]
summary['original_pilot']={'n':len(pilot),'saturated':sum(min(r['probabilities']['p1_conditional'],1-r['probabilities']['p1_conditional'])<=.001 for r in pilot),'middle':sum(.1<r['probabilities']['p1_conditional']<.9 for r in pilot),'max_normalization_error':max(abs(r['probabilities']['p1_conditional']-1/(1+math.exp(r['probabilities']['logp0']-r['probabilities']['logp1']))) for r in pilot)}
db=sqlite3.connect(BASE/'budget.sqlite');summary['budget']=[dict(zip(['state','count','accounted_usd','actual_usd'],r)) for r in db.execute('select state,count(*),sum(charged)/1e9,sum(cast(actual_cost as real)) from attempts group by state')]
summary['anomaly']=[g for g in groupstats if g['pair']=='conservatism--16204']
protected=json.loads((BASE/'prior-preservation.json').read_text());summary['old_evidence_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected['protected_files_sha256'].items());assert summary['old_evidence_unchanged']
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for name in ['selection.json','prior-preservation.json','earlier-anomaly-generation-metadata.json','architecture.json']:(OUT/name).write_bytes((BASE/name).read_bytes())
print(json.dumps(summary,indent=2))
# Sensitivity only: 19 measured cells resampled; all other 461 cells held fixed.
import random
rng=random.Random(20261020);cs=sorted({r['constitution_id'] for r in pilot});ss=sorted({r['scenario_id'] for r in pilot});original={(r['constitution_id'],r['scenario_id']):r['probabilities']['p1_conditional'] for r in pilot}
repeats=defaultdict(list)
for r in rows:
 if r['phase']=='seq-no-seed':repeats[tuple(r['pair'].split('--'))].append(r['p'])
draws=defaultdict(list)
for _ in range(1000):
 m=dict(original)
 for k,v in repeats.items():m[k]=rng.choice(v)
 for j,c in enumerate(cs):
  for d in cs[j+1:]:draws[(c,d)].append(sum(abs(m[c,s]-m[d,s]) for s in ss)/len(ss))
def quant(v,q):v=sorted(v);return v[round(q*(len(v)-1))]
impact=[]
for (c,d),v in draws.items():impact.append({'constitution_a':c,'constitution_b':d,'mean_distance':statistics.mean(v),'p025':quant(v,.025),'p975':quant(v,.975),'interval_width':quant(v,.975)-quant(v,.025),'range':max(v)-min(v)})
impact.sort(key=lambda x:-x['interval_width']);(OUT/'partial-distance-sensitivity.json').write_text(json.dumps({'seed':20261020,'draws':1000,'measured_cells':19,'fixed_cells':461,'warning':'Sensitivity demonstration, not a confidence interval for full experiment. Three repeats only; assumes independent draws and holds 461 potentially unstable cells fixed. Sequential unseeded condition; recovery happened later.','pairs':impact},indent=2)+'\n');print('Largest partial distance spread:',impact[0])
