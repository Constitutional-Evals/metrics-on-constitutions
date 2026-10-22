"""Offline pilot diagnostics. No API calls; requires matplotlib only for plots."""
import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import sqlite3
import statistics

from constitution_distance.core import digest, distance_matrix, extract_probabilities


def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();base=args.runs;out=args.output;out.mkdir(parents=True,exist_ok=True)
    records={phase:[json.loads(l) for l in (base/phase/'responses.jsonl').read_text().splitlines()] for phase in ['smoke','pilot','repeats']}
    main_rs=records['pilot'];all_rs=sum(records.values(),[])
    manifest=json.loads((base/'pilot/manifest.json').read_text());cs=manifest['spec']['constitutions'];ss=manifest['spec']['scenarios']
    cids=[c['id'] for c in cs];sids=[s['id'] for s in ss]
    by={(r['constitution_id'],r['scenario_id']):r for r in main_rs}
    assert len(by)==len(main_rs)
    for r in all_rs:
        assert extract_probabilities(r['response'])==r['probabilities']
        assert r['prompt_hash']==digest(r['request']['messages']) and r['request_hash']==digest(r['request'])
    vectors=[[by[(c,s)]['probabilities']['p1_conditional'] if (c,s) in by else None for s in sids] for c in cids]
    complete_rows=[i for i,v in enumerate(vectors) if all(p is not None for p in v)]
    dist=[[0. if i==j else math.fsum(abs(a-b) for a,b in zip(x,y)) if i in complete_rows and j in complete_rows else None
           for j,y in enumerate(vectors)] for i,x in enumerate(vectors)]
    known=[p for v in vectors for p in v if p is not None]
    checks={'probability_shape':[len(vectors),len(vectors[0])],'distance_shape':[len(dist),len(dist[0])],
            'probabilities_in_range':all(0<=p<=1 and math.isfinite(p) for p in known),
            'symmetric_including_missing_mask':all(dist[i][j]==dist[j][i] for i in range(24) for j in range(24)),
            'zero_diagonal':all(dist[i][i]==0 for i in range(24)),
            'nonnegative_known_distances':all(d>=0 for row in dist for d in row if d is not None),
            'triangle_inequality_on_complete_rows':all(dist[i][k]<=dist[i][j]+dist[j][k]+1e-12 for i in complete_rows for j in complete_rows for k in complete_rows),
            'missing_probability_cells':len(cids)*len(sids)-len(main_rs),
            'missing_distance_cells':sum(d is None for row in dist for d in row),
            'complete_constitution_vectors':len(complete_rows)}
    for key in ['probabilities_in_range','symmetric_including_missing_mask','zero_diagonal','nonnegative_known_distances','triangle_inequality_on_complete_rows']:assert checks[key]
    for name,cols,rows in [('probabilities_conditional.csv',sids,vectors),('distances_l1.csv',cids,dist),('distances_mean_l1.csv',cids,[[d/20 if d is not None else None for d in row] for row in dist])]:
        with (out/name).open('w',newline='') as f:
            w=csv.writer(f,lineterminator="\n");w.writerow(['constitution_id']+cols);w.writerows([[c]+row for c,row in zip(cids,rows)])
    with (out/'probabilities_long.csv').open('w',newline='') as f:
        cols=['constitution_id','scenario_id','returned_token','logp0','logp1','p0','p1','p1_conditional','binary_mass','prompt_tokens','completion_tokens','cost_usd','model','provider','prompt_hash','request_hash']
        w=csv.DictWriter(f,fieldnames=cols,lineterminator="\n");w.writeheader()
        for r in main_rs:
            w.writerow({'constitution_id':r['constitution_id'],'scenario_id':r['scenario_id'],
                'returned_token':r['response']['choices'][0]['message']['content'],**r['probabilities'],
                'prompt_tokens':r['response']['usage']['prompt_tokens'],'completion_tokens':r['response']['usage']['completion_tokens'],
                'cost_usd':r['response']['usage']['cost'],'model':r['response']['model'],'provider':r['response']['provider'],
                'prompt_hash':r['prompt_hash'],'request_hash':r['request_hash']})
    pair_dist=[(dist[i][j],cids[i],cids[j]) for i in complete_rows for j in complete_rows if i<j]
    per_scenario=[]
    for j,s in enumerate(sids):
        vals=[v[j] for v in vectors if v[j] is not None]
        per_scenario.append({'id':s,'n':len(vals),'min':min(vals),'max':max(vals),'range':max(vals)-min(vals),'stddev':statistics.pstdev(vals)})
    with (out/'scenario_variation.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(per_scenario[0]),lineterminator="\n");w.writeheader();w.writerows(per_scenario)
    main_logs=[r['probabilities'][k] for r in main_rs for k in ['logp0','logp1']]
    margins=[r['probabilities']['logp1']-r['probabilities']['logp0'] for r in main_rs]
    numerical={'logprob_min':min(main_logs),'logprob_max':max(main_logs),'exact_zero_logprobs':sum(x==0 for x in main_logs),
        'label_logprob_count':len(main_logs),'sentinel_logprobs':sum(x<=-999 for x in main_logs),
        'fraction_log_odds_within_1e-5_of_1_16_grid':sum(abs(x*16-round(x*16))<1e-5 for x in margins)/len(margins),
        'binary_mass_min':min(r['probabilities']['binary_mass'] for r in main_rs),
        'binary_mass_max':max(r['probabilities']['binary_mass'] for r in main_rs),
        'interpretation':'Exact zero winning logprobs and near-grid log odds indicate finite precision/rounding consistent with FP8 serving. No missing-token sentinel was accepted. Cannot distinguish all provider clipping/transforms from API data alone.'}
    repeated=defaultdict(list)
    targeted={r['request_hash'] for r in records['repeats']}
    for phase,rs in records.items():
        for r in rs:
            if r['request_hash'] in targeted:
                repeated[r['request_hash']].append({'phase':phase,'replica':r['replica'],
                    'constitution_id':r['constitution_id'],'scenario_id':r['scenario_id'],
                    'probability':r['probabilities']['p1_conditional'],
                    'logp0':r['probabilities']['logp0'],'logp1':r['probabilities']['logp1']})
    repeat_report=[]
    for request_hash,rs in repeated.items():
        vals=[r['probability'] for r in rs]
        repeat_report.append({'request_hash':request_hash,'constitution_id':rs[0]['constitution_id'],'scenario_id':rs[0]['scenario_id'],
            'n':len(rs),'identical_probabilities':len(set(vals))==1,'max_absolute_range':max(vals)-min(vals),
            'min':min(vals),'max':max(vals),'observations':rs})
    db=sqlite3.connect(base/'task-budget.sqlite');db.row_factory=sqlite3.Row
    attempts=[dict(r) for r in db.execute('select * from attempts order by started,id')]
    state_counts=dict(Counter(a['state'] for a in attempts))
    costs={'known_actual_cost_usd':math.fsum(float(a['actual_cost']) for a in attempts if a['actual_cost'] is not None),
        'unknown_cost_attempts':sum(a['actual_cost'] is None for a in attempts),
        'conservative_total_usd':sum(a['charged'] for a in attempts)/1e9,
        'held_reservations_usd':sum(a['reserve'] for a in attempts if a['state']=='reserved')/1e9,
        'budget_usd':db.execute('select cap from settings where id=1').fetchone()[0]/1e9,
        'total_dispatches':len(attempts),'attempt_state_counts':state_counts,
        'http_status_counts':dict(Counter(str(a['http_status']) for a in attempts)),
        'phase_costs':{phase:math.fsum(r['response']['usage']['cost'] for r in rs) for phase,rs in records.items()},
        'successful_input_tokens':sum(r['response']['usage']['prompt_tokens'] for r in all_rs),
        'successful_output_tokens':sum(r['response']['usage']['completion_tokens'] for r in all_rs)}
    tc=json.loads((base/'token-counts.json').read_text());st={s['id']:s['tokens'] for s in tc['scenarios']}
    offsets=Counter(r['response']['usage']['prompt_tokens']-tc['systems'][r['constitution_id']]-st[r['scenario_id']] for r in all_rs)
    assert len(offsets)==1
    overhead=next(iter(offsets));full_n=24*1360
    full_tokens=1360*sum(tc['systems'].values())+24*sum(st.values())+full_n*overhead
    max_tokens=max(tc['systems'].values())+max(st.values())+overhead
    full_cost={'pairs':full_n,'estimated_input_tokens':full_tokens,'output_tokens':full_n,'observed_template_overhead_tokens':overhead,
        'template_overhead_matched_responses':sum(offsets.values()),'max_prompt_tokens':max_tokens,
        'uncached_usd':full_tokens*.22/1e6+full_n*.5/1e6,
        'idealized_all_input_cached_floor_usd':full_tokens*.11/1e6+full_n*.5/1e6,
        'pilot_average_cost_extrapolation_usd':math.fsum(r['response']['usage']['cost'] for r in main_rs)/len(main_rs)*full_n,
        'excludes':'Retries, unknown charges, provider changes and any future prompt/action corrections; caching is not guaranteed.'}
    result={'checks':checks,'missing':[{'constitution_id':c,'scenario_id':s} for c in cids for s in sids if (c,s) not in by],
        'provider_counts':dict(Counter(r['response']['provider'] for r in all_rs)),
        'model_counts':dict(Counter(r['response']['model'] for r in all_rs)),
        'both_labels_available_valid_responses':len(all_rs),'numerical':numerical,'costs':costs,'full_projection':full_cost,
        'variation':{'known_probability_min':min(known),'known_probability_max':max(known),
            'fraction_between_005_and_095':sum(.05<p<.95 for p in known)/len(known),
            'complete_pair_count':len(pair_dist),'minimum_summed_l1':min(pair_dist),
            'maximum_summed_l1':max(pair_dist),'mean_summed_l1':statistics.mean(d for d,_,_ in pair_dist),
            'zero_distance_pairs':sum(d==0 for d,_,_ in pair_dist),
            'largest_scenario_ranges':sorted(per_scenario,key=lambda x:x['range'],reverse=True)[:5]},
        'reproducibility':repeat_report}
    (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    # Scientific plots use the standard plotting library, with missing values gray.
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    for data,xlabels,title,name,scale in [(vectors,sids,'Conditional action-1 probability (gray = missing)','probability_heatmap.png',1),
        (dist,cids,'Summed L1 across 20 dilemmas (gray = unknown)','distance_heatmap.png',None)]:
        arr=np.array([[np.nan if v is None else v for v in row] for row in data]);cmap=plt.get_cmap('viridis').copy();cmap.set_bad('#bdbdbd')
        fig,ax=plt.subplots(figsize=(14,9));im=ax.imshow(arr,aspect='auto',vmin=0,vmax=scale,cmap=cmap)
        ax.set_xticks(range(len(xlabels)),xlabels,rotation=90,fontsize=8);ax.set_yticks(range(len(cids)),cids,fontsize=8)
        ax.set_title(title);fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(out/name,dpi=160);plt.close(fig)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
