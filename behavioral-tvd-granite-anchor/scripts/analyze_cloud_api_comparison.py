"""No inference: regenerate cloud candidate statistics from saved evidence."""
import csv,json,math,pathlib,sqlite3,statistics,sys,hashlib
from collections import defaultdict
sys.path.insert(0,str(pathlib.Path(__file__).parent));import cloud_api_comparison as c
B=c.BASE;O=pathlib.Path('results/cloud-api-comparison');O.mkdir(parents=True,exist_ok=True)
rows=[];groups=defaultdict(list)
for f in sorted(B.glob('*/responses.jsonl')):
 for l in f.read_text().splitlines():
  r=json.loads(l);i=r['item'];a=r['response'];p=r['result'];row={'candidate':i['candidate'],'phase':i['phase'],'pair':i['source_id'],'replica':i['replica'],'p':p['p1_conditional'],'logp0':p['logp0'],'logp1':p['logp1'],'log_odds':p['log_odds'],'p0':p['p0'],'p1':p['p1'],'binary_mass':p['binary_mass'],'sampled':p['sampled_output'],'compliant':p['format_compliant'],'model':a['model'],'provider':a['provider'],'response_id':a['id'],'fingerprint':a.get('system_fingerprint'),'request_hash':r['request_hash'],'wire_hash':a.get('_transport',{}).get('request_body_sha256'),'prompt_hash':r['prompt_hash'],'input_tokens':a['usage']['prompt_tokens'],'output_tokens':a['usage']['completion_tokens'],'cost':a['usage']['cost']};rows.append(row);groups[(row['candidate'],row['phase'],row['pair'])].append(row)
if rows:
 with (O/'evaluations.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
gstats=[]
for (name,phase,pair),rs in groups.items():
 ps=[r['p'] for r in rs];ds=[r['log_odds'] for r in rs];gstats.append({'candidate':name,'phase':phase,'pair':pair,'n':len(rs),'mean_p':statistics.mean(ps),'min_p':min(ps),'max_p':max(ps),'range_p':max(ps)-min(ps),'range_log_odds':max(ds)-min(ds),'unique_p':len(set(ps)),'unique_request_hashes':len({r['request_hash'] for r in rs}),'unique_wire_hashes':len({r['wire_hash'] for r in rs})})
with (O/'repeat-groups.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(gstats[0]),lineterminator='\n');w.writeheader();w.writerows(gstats)
pilot=[json.loads(l) for l in pathlib.Path('/workspace/work/controlled-v2/pilot/responses.jsonl').read_text().splitlines()];old={(r['constitution_id']+'--'+r['scenario_id']):r for r in pilot}
summary={}
for name,(model,tag) in c.CANDIDATES.items():
 e=next(e for e in json.loads((B/(model.replace('/','--')+'.json')).read_text())['data']['endpoints'] if e['tag']==tag)
 rr=[r for r in rows if r['candidate']==name];screen=[r for r in rr if r['phase']=='screen'];ratios=[r['input_tokens']/old[r['pair']]['response']['usage']['prompt_tokens'] for r in screen]
 price={k:float(e['pricing'][k])*1e6 for k in ['prompt','completion']};inp=96464288*statistics.mean(ratios) if ratios else None
 s={'model':model,'provider':tag,'quantization_advertised':e.get('quantization'),'context':e['context_length'],'pricing_usd_per_million':price,'valid_responses':len(rr),'screen_valid':len(screen),'screen_middle_ids':[r['pair'] for r in screen if .1<r['p']<.9],'screen_saturated':sum(min(r['p'],1-r['p'])<=.001 for r in screen),'format_compliant':sum(r['compliant'] for r in rr),'known_valid_cost':sum(r['cost'] for r in rr),'estimated_32064_uncached_usd':inp/1e6*price['prompt']+32064/1e6*price['completion'] if inp else None,'estimated_32640_uncached_usd':(inp/1e6*price['prompt']+32064/1e6*price['completion'])*32640/32064 if inp else None,'phases':{}}
 for phase in sorted({r['phase'] for r in rr}):
  gs=[g for g in gstats if g['candidate']==name and g['phase']==phase];s['phases'][phase]={'valid':sum(g['n'] for g in gs),'groups':len(gs),'max_probability_range':max(g['range_p'] for g in gs),'median_probability_range':statistics.median(g['range_p'] for g in gs),'max_log_odds_range':max(g['range_log_odds'] for g in gs),'nonidentical_groups':sum(g['unique_p']>1 for g in gs),'tolerance_fail_groups':sum(g['n']>=2 and (g['range_p']>.001 or g['range_log_odds']>.01) for g in gs)}
 a={g['pair']:g for g in gstats if g['candidate']==name and g['phase']=='repeat-sequential'};d={g['pair']:g for g in gstats if g['candidate']==name and g['phase']=='repeat-concurrent'}
 if a and d:
  diffs=[abs(a[k]['mean_p']-d[k]['mean_p']) for k in a.keys()&d.keys()];s['concurrency_mean_difference']={'mean':statistics.mean(diffs),'max':max(diffs)}
 summary[name]=s
(O/'candidate-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
db=sqlite3.connect(B/'budget.sqlite');budget=[dict(zip(['state','count','accounted_usd','actual_usd'],r)) for r in db.execute('select state,count(*),sum(charged)/1e9,sum(cast(actual_cost as real)) from attempts group by state')];(O/'budget-summary.json').write_text(json.dumps(budget,indent=2)+'\n')
print('BUDGET',budget)
for k,s in summary.items():print(k,s['screen_valid'],'mid',len(s['screen_middle_ids']),'costfull',s['estimated_32640_uncached_usd'],'phases',[(p,v['valid'],round(v['max_probability_range'],6),v['tolerance_fail_groups']) for p,v in s['phases'].items() if 'repeat' in p])
# Each newly evaluated 24x3 block is separate from every earlier experiment.
from constitution_distance.core import distance_matrix
for name in c.CANDIDATES:
 rs=[r for r in rows if r['candidate']==name and r['phase']=='coverage24x3']
 if len(rs)!=72:continue
 table={tuple(r['pair'].split('--')):r['p'] for r in rs};cs=sorted({x[0] for x in table});ss=sorted({x[1] for x in table});vectors=[[table[cid,s] for s in ss] for cid in cs];d=distance_matrix(vectors)
 with (O/(name+'-coverage-probabilities.csv')).open('w') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['constitution']+ss);w.writerows([[cid]+v for cid,v in zip(cs,vectors)])
 for label,matrix in [('summed-l1',d),('mean-l1',[[v/len(ss) for v in r] for r in d])]:
  with (O/(name+'-coverage-'+label+'.csv')).open('w') as f:
   w=csv.writer(f,lineterminator='\n');w.writerow(['constitution']+cs);w.writerows([[cid]+v for cid,v in zip(cs,matrix)])
 info={'candidate':name,'scenarios':ss,'constitutions':24,'valid_cells':len(rs),'format_compliant':sum(r['compliant'] for r in rs),'input_token_range':[min(r['input_tokens'] for r in rs),max(r['input_tokens'] for r in rs)],'probability_range':[min(r['p'] for r in rs),max(r['p'] for r in rs)],'per_scenario_constitution_spread':{s:max(table[cid,s] for cid in cs)-min(table[cid,s] for cid in cs) for s in ss},'unique_vectors':len({tuple(v) for v in vectors}),'summed_distance_range':[min(d[i][j] for i in range(24) for j in range(i+1,24)),max(d[i][j] for i in range(24) for j in range(i+1,24))],'interpretation':'Format adherence and probability sensitivity are evidence of operational suitability, not proof of faithful ethical reasoning; only3 scenarios.'}
 (O/(name+'-coverage-summary.json')).write_text(json.dumps(info,indent=2)+'\n')
 print('COVERAGE',info)
# Availability includes invalid/HTTP failures, not just successful score rows.
db.row_factory=sqlite3.Row
availability={n:{'attempts':0,'valid':0,'invalid':0,'http_errors':{},'errors':[],'usage_reported_cost':0} for n in c.CANDIDATES}
for a in db.execute('SELECT a.*,r.spec FROM attempts a JOIN runs r ON a.run=r.id'):
 spec=json.loads(a['spec']);name=spec['items'][0]['candidate'];v=availability[name];v['attempts']+=1
 if a['state'] in ['valid','invalid']:v[a['state']]+=1
 if a['http_status'] and a['http_status']>=400:v['http_errors'][str(a['http_status'])]=v['http_errors'].get(str(a['http_status']),0)+1
 if a['error']:v['errors'].append(a['error'])
 if a['actual_cost'] is not None:v['usage_reported_cost']+=float(a['actual_cost'])
(O/'availability.json').write_text(json.dumps(availability,indent=2)+'\n')
rr=[r for r in rows if r['candidate']=='granite3-cloudflare'];gg=defaultdict(list)
for r in rr:gg[r['pair']].append(r)
confirmation={'valid_responses':len(rr),'unique_response_ids':len({r['response_id'] for r in rr}),'format_compliant':sum(r['compliant'] for r in rr),'main_intermediate_pairs':len(summary['granite3-cloudflare']['screen_middle_ids']),'all_phase_max_ranges':{k:max(max(r[k] for r in v)-min(r[k] for r in v) for v in gg.values()) for k in ['p','logp0','logp1','log_odds']},'per_pair_request_hashes':{k:len({r['request_hash'] for r in v}) for k,v in gg.items()},'per_pair_wire_hashes':{k:len({r['wire_hash'] for r in v}) for k,v in gg.items()},'binary_mass_range':[min(r['binary_mass'] for r in rr),max(r['binary_mass'] for r in rr)],'sampled_counts':{s:sum(r['sampled']==s for r in rr) for s in ['0','1']},'confirmatory_phases':{p:summary['granite3-cloudflare']['phases'][p] for p in summary['granite3-cloudflare']['phases'] if p.startswith('confirm-')},'warning':'Bounded API repeatability evidence, not guaranteed immutable weights or long-term determinism. All original messages unchanged.'}
assert all(v==0 for v in confirmation['all_phase_max_ranges'].values());assert all(v==1 for v in confirmation['per_pair_request_hashes'].values());assert all(v==1 for v in confirmation['per_pair_wire_hashes'].values())
(O/'recommended-confirmation.json').write_text(json.dumps(confirmation,indent=2)+'\n')
