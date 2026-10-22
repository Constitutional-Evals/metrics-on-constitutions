"""Offline research supplement; no API client, database, dispatcher or mutation.

Reconstruct semantic probabilities independently from genuine raw label logs,
verify official exports exactly, and select a complete common scenario grid.
The supplied numerical targets are checked only after independent calculation.
"""
import argparse
import contextlib
import csv
import gzip
import hashlib
import html
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import socket
import subprocess
from unittest.mock import patch

import numpy as np

RID='03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e'
METRICS=('A_primary','B_secondary','C_canonical')
CONDITIONS=('canonical','labels_swapped','order_reversed','both_reversed')
PAIRS=[('lockean-rights','marxism','distant'),('utilitarianism','kantian-deontology','distant'),
       ('ubuntu','care-ethics','close'),('buen-vivir','environmental-ethics','close')]
BASELINE='__baseline__'
DEFAULT_OUT=Path('results/granite-exploratory/supplementary-complete-case-0239')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def sigmoid(delta):
    return 1/(1+math.exp(-delta)) if delta>=0 else math.exp(delta)/(1+math.exp(delta))


def raw_semantic(response, swapped):
    """Use next-token distribution, never sampled output or self-report."""
    choices=response.get('choices')
    if not isinstance(choices,list) or len(choices)!=1:raise ValueError('One completion required')
    entries=(choices[0].get('logprobs') or {}).get('content')
    if not isinstance(entries,list) or len(entries)!=1:raise ValueError('Missing next-token log probabilities')
    first=entries[0];logs={}
    for token in [first]+list(first.get('top_logprobs') or []):
        label=token.get('token')
        if label not in ('0','1'):continue
        lp=token.get('logprob')
        if type(lp) not in (int,float) or not math.isfinite(lp) or not -999<lp<=0 or token.get('bytes')!=[ord(label)]:
            raise ValueError('Invalid ASCII label log probability')
        if label in logs and logs[label]!=lp:raise ValueError('Conflicting duplicate token log probabilities')
        logs[label]=lp
    if set(logs)!={'0','1'}:raise ValueError('Both token probabilities required; no zero substitution')
    mass=math.exp(logs['0'])+math.exp(logs['1'])
    if not 0<mass<=1.00001:raise ValueError('Invalid binary probability mass')
    delta=logs['0']-logs['1'] if swapped else logs['1']-logs['0']
    return sigmoid(delta),logs,mass


def complete_mask(p, baseline):
    if p.ndim!=3 or p.shape[0]!=4 or baseline.shape!=(4,p.shape[2]):raise ValueError('Invalid common grid')
    return np.isfinite(p).all(axis=(0,1)) & np.isfinite(baseline).all(axis=0)


def calculate(p):
    if p.ndim!=3 or p.shape[0]!=4 or p.shape[-1]<1 or not np.isfinite(p).all() or not ((p>=0)&(p<=1)).all():
        raise ValueError('Complete finite probabilities in [0,1] required')
    q=p.mean(axis=0);n=p.shape[-1]
    summed={'A_primary':np.abs(q[:,None,:]-q[None,:,:]).sum(-1),
            'B_secondary':np.abs(p[:,:,None,:]-p[:,None,:,:]).sum(-1).mean(0),
            'C_canonical':np.abs(p[0,:,None,:]-p[0,None,:,:]).sum(-1)}
    if not np.all(summed['A_primary']<=summed['B_secondary']+1e-12):raise AssertionError('A must be <= B')
    max_scalar=0.;triangle={}
    # Independent scalar fsum reconstruction checks every matrix cell.
    for name,d in summed.items():
        assert np.array_equal(d,d.T) and np.all(d.diagonal()==0) and (d>=0).all()
        for i in range(p.shape[1]):
            for j in range(p.shape[1]):
                if name=='A_primary':v=math.fsum(abs(math.fsum(float(p[k,i,s]) for k in range(4))/4-math.fsum(float(p[k,j,s]) for k in range(4))/4) for s in range(n))
                elif name=='B_secondary':v=math.fsum(abs(float(p[k,i,s])-float(p[k,j,s])) for k in range(4) for s in range(n))/4
                else:v=math.fsum(abs(float(p[0,i,s])-float(p[0,j,s])) for s in range(n))
                max_scalar=max(max_scalar,abs(v-d[i,j]));assert abs(v-d[i,j])<1e-12
        triangle[name]=max(0.,max(float(d[i,j]-d[i,k]-d[k,j])/n for i in range(p.shape[1]) for j in range(p.shape[1]) for k in range(p.shape[1])))
        assert triangle[name]<1e-12
    return q,summed,{'maximum_independent_scalar_error':max_scalar,'maximum_normalized_triangle_violations':triangle,
                     'probabilities_complete_in_range':True,'symmetry_exact_zero_diagonals_nonnegative':True,'A_le_B':True}


def ranked_pairs(d, ids):
    pairs=sorted((float(d[i,j]),ids[i],ids[j]) for i in range(len(ids)) for j in range(i+1,len(ids)))
    values=[r[0] for r in pairs]
    return [{'constitution_a':a,'constitution_b':b,'normalized_distance':v,
             'rank_closest_first':1+sum(x<v for x in values),'rank_max_if_tied':sum(x<=v for x in values),
             'ordinal_rank_id_tiebreak':k} for k,(v,a,b) in enumerate(pairs,1)]


def matrix(path, a, rows, columns):
    with Path(path).open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['constitution']+list(columns));w.writerows([[c]+list(v) for c,v in zip(rows,a)])


def table(path, rows):
    with Path(path).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def read_matrix(path):
    with Path(path).open() as f:r=list(csv.reader(f))
    return [x[0] for x in r[1:]],r[0][1:],np.asarray([[float(x) for x in row[1:]] for row in r[1:]])


def load_records(manifest):
    ids=[s for b in manifest['batches'][:12] for s in b['scenario_ids']];cs=manifest['constitution_order']
    p=np.full((4,24,len(ids)),np.nan);base=np.full((4,len(ids)),np.nan);seen=set();counts={};mass=[];odds=[]
    with gzip.open('data/granite-exploratory/task-plan.jsonl.gz','rt') as f:
        plan={tuple(r['pair']):r for r in map(json.loads,f) if r['batch']<=12 and r['kind']!='canary'}
    maxprob=0.;all_raw_semantic_exact=True;files={}
    for batch in range(1,13):
        path=Path(f'results/granite-exploratory/batch-{batch:04d}/responses.jsonl.gz');files[str(path)]=sha(path)
        with gzip.open(path,'rt') as f:
            for r in map(json.loads,f):
                item=r['item'];kind=item['kind'];counts[kind]=counts.get(kind,0)+1
                if kind=='canary':continue
                pair=tuple(item['pair']);cid,sid,k=pair
                if pair in seen:raise ValueError('Duplicate scientific record')
                seen.add(pair)
                assert r['run_id']==RID and r['stage']==f'batch-{batch:04d}'
                assert r['request_hash']==digest(r['request'])==plan[pair]['request_hash']
                assert r['prompt_hash']==digest(r['request']['messages'])==plan[pair]['prompt_hash']
                assert {k:v for k,v in r['request'].items() if k!='messages'}==manifest['settings']
                assert len(r['request']['messages'])==2 and [x['role'] for x in r['request']['messages']]==['system','user']
                assert r['response']['model']==manifest['settings']['model'] and r['response']['provider']=='Cloudflare'
                assert item['swapped']==manifest['conditions'][k]['swapped'] and item['condition']==CONDITIONS[k]
                v,logs,m=raw_semantic(r['response'],item['swapped']);result=r['result']
                for label in ['0','1']:assert logs[label]==result['logp'+label]
                assert math.isclose(m,result['binary_mass'],rel_tol=0,abs_tol=1e-15)
                assert v==result['p_to_do'];all_raw_semantic_exact &= v==result['p_to_do']
                # Independent exp-normalization may differ by the last FP bit.
                ratio=math.exp(logs['1'])/m;semantic_ratio=1-ratio if item['swapped'] else ratio
                maxprob=max(maxprob,abs(v-semantic_ratio));assert abs(v-semantic_ratio)<1e-12
                if cid==BASELINE:base[k,ids.index(sid)]=v
                else:p[k,cs.index(cid),ids.index(sid)]=v
                mass.append(m);odds.append(logs['1']-logs['0'])
    assert counts=={'primary':23039,'baseline':960,'canary':372}
    missing=[{'constitution':cs[c],'scenario':ids[s],'condition':CONDITIONS[k]} for k,c,s in np.argwhere(~np.isfinite(p))]
    assert missing==[{'constitution':'ubuntu','scenario':'29912','condition':'labels_swapped'}]
    assert np.isfinite(base).all() and len(seen)==23999
    return ids,cs,p,base,{'source_archives_sha256':files,'observed_record_counts':counts,'missing_primary':missing,
                        'maximum_exp_ratio_probability_difference':maxprob,'all_raw_semantic_values_equal_archived_probabilities_exactly':all_raw_semantic_exact,
                        'minimum_answer_token_mass':min(mass),'fraction_log_odds_on_0_125_grid_tolerance_1e_5':float(np.mean([abs(x-.125*round(x/.125))<1e-5 for x in odds]))}


def display_table(out, d, cs, names, n, scope):
    warning=('Supplementary complete-case result, not completed Batch 12 or the official experiment. Dilemma 29912 is excluded for every constitution because one required probability is missing.' if n==239 else 'Official last-completed-batch prefix: 220 scenarios, not the full 1,336-scenario experiment.')
    text=f'# Full primary A distance matrix — {n} scenarios\n\n{scope}. {warning}\n\nNormalized L1 / mean binary total variation. Values displayed to 6 decimal places; [CSV](distances-A_primary-normalized-l1.csv) retains full floating precision. Both axes follow the full names below.\n\n'
    text+='| Constitution | '+' | '.join(names[c] for c in cs)+' |\n'+'|---|'+'---:|'*len(cs)+'\n'
    for i,c in enumerate(cs):text+='| '+names[c]+' | '+' | '.join(f'{v:.6f}' for v in d[i])+' |\n'
    (out/'primary-distance-table.md').write_text(text)
    def cells():
        rows=[]
        for i,c in enumerate(cs):
            row='<tr><th scope="row">'+html.escape(names[c])+'</th>'
            row+=''.join(f'<td title="{html.escape(names[c])} ↔ {html.escape(names[c2])}: {d[i,j]:.17g}">{d[i,j]:.6f}</td>' for j,c2 in enumerate(cs));rows.append(row+'</tr>')
        return ''.join(rows)
    headers=''.join('<th scope="col"><span>'+html.escape(names[c])+'</span></th>' for c in cs)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Primary behavioral distance matrix</title>
<style>body{font:16px system-ui,sans-serif;margin:2rem;color:#162337;background:#fff}a{color:#005bbb}.scroll{overflow:auto;max-height:80vh;border:1px solid #bbc}table{border-collapse:separate;border-spacing:0;font-variant-numeric:tabular-nums}th,td{padding:.5rem;border-right:1px solid #dde;border-bottom:1px solid #dde;white-space:nowrap}thead th{position:sticky;top:0;background:#eaf0f6;z-index:2}thead th span{writing-mode:vertical-rl;transform:rotate(180deg);height:16rem;text-align:left}tbody th{position:sticky;left:0;background:#f4f7fa;z-index:1;text-align:left}td{font-size:.8rem;text-align:right}tbody tr:hover td{background:#fff0b5}caption{text-align:left;padding:1rem}h1{font-size:1.6rem}.note{max-width:80ch}</style>'''
    page+=f'<h1>Primary A — {n} scenarios</h1><p class="note">{html.escape(scope)}. {html.escape(warning)}</p><p>Full constitution names on both axes. Display rounded to 6 decimals; hover for full precision. <a href="distances-A_primary-normalized-l1.csv">Full-precision CSV</a> · <a href="primary-distance-heatmap.svg">Accessible SVG heatmap</a> · <a href="constitutions.csv">Names and immutable IDs</a></p><div class="scroll" tabindex="0" aria-label="Scrollable full primary distance table"><table><caption>Normalized L1 = mean binary total variation. N={n}. Zero diagonal; symmetric.</caption><thead><tr><th scope="col">Constitution</th>{headers}</tr></thead><tbody>{cells()}</tbody></table></div></html>'
    (out/'primary-distance-table.html').write_text(page)


def heatmap(out,d,cs,names,n,scope):
    import os
    os.environ.setdefault('MPLCONFIGDIR','/tmp/granite-research-mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'granite-research-239-v1','pdf.fonttype':42})
    labels=[names[c] for c in cs];fig,ax=plt.subplots(figsize=(16,15),layout='constrained')
    im=ax.imshow(d,cmap='cividis',vmin=0,vmax=float(d.max()),interpolation='nearest')
    ax.set_xticks(range(24),labels=labels,rotation=90,fontsize=9);ax.set_yticks(range(24),labels=labels,fontsize=9)
    ax.set_title(f'Granite-conditioned behavioral distance A\n{scope}: N={n}',fontsize=14,pad=15)
    fig.colorbar(im,ax=ax,shrink=.72,label='Mean binary total variation / normalized L1')
    fig.savefig(out/'primary-distance-heatmap.png',dpi=180)
    fig.savefig(out/'primary-distance-heatmap.svg',metadata={'Date':None,'Description':f'{scope}, {n} scenarios; full matrix available as CSV and HTML.'})
    fig.savefig(out/'primary-distance-heatmap.pdf',metadata={'CreationDate':None,'ModDate':None,'Title':f'{scope}: primary A, N={n}'})
    plt.close(fig)
    path=out/'primary-distance-heatmap.svg';text=path.read_text();start=text.index('<svg');end=text.index('>',start)
    text=text[:end]+' role="img" aria-labelledby="matrix-title matrix-description"'+text[end:]
    end=text.index('>',start)+1
    text=text[:end]+f'<title id="matrix-title">Primary behavioral distance A, {n} scenarios</title><desc id="matrix-description">{html.escape(scope)}. Both axes list all 24 full constitution names. Darker cells indicate smaller mean binary total variation; diagonal values are zero. Use the accompanying HTML or CSV table for precise accessible values.</desc>'+text[end:]
    path.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')


def export_scope(out,p,baseline,ids,cs,names,scope):
    out.mkdir(parents=True,exist_ok=True);n=len(ids);q,sums,proof=calculate(p);tri=np.triu_indices(len(cs),1)
    matrix(out/'probabilities-counterbalanced.csv',q,cs,ids)
    for k,name in enumerate(CONDITIONS):matrix(out/f'probabilities-{name}.csv',p[k],cs,ids)
    stats={};rankings={}
    for name,d in sums.items():
        matrix(out/f'distances-{name}-summed-l1.csv',d,cs,cs);matrix(out/f'distances-{name}-normalized-l1.csv',d/n,cs,cs)
        v=d[tri]/n;stats[name]={'mean_normalized':float(v.mean()),'minimum_normalized':float(v.min()),'median_normalized':float(np.median(v)),
                              'maximum_normalized':float(v.max()),'mean_summed_l1':float(d[tri].mean())}
        rankings[name]=ranked_pairs(d/n,cs)
        for r in rankings[name]:r.update(constitution_a_name=names[r['constitution_a']],constitution_b_name=names[r['constitution_b']])
        table(out/f'pairs-{name}-ranked.csv',rankings[name])
    table(out/'constitutions.csv',[{'id':c,'full_name':names[c]} for c in cs])
    table(out/'baseline.csv',[{'scenario':s,**{CONDITIONS[k]:float(baseline[k,j]) for k in range(4)},'counterbalanced':float(baseline[:,j].mean())} for j,s in enumerate(ids)])
    labels=(p[1]+p[3]-p[0]-p[2])/2;order=(p[2]+p[3]-p[0]-p[1])/2;shifts=q-baseline.mean(0)
    sensitivity={'mean_absolute_label_effect':float(np.abs(labels).mean()),'mean_absolute_action_order_effect':float(np.abs(order).mean()),'mean_four_condition_range':float(np.ptp(p,axis=0).mean()),
                 'mean_absolute_constitution_to_baseline_shift':float(np.abs(shifts).mean()),'mean_signed_constitution_to_baseline_shift':float(shifts.mean())}
    display_table(out,sums['A_primary']/n,cs,names,n,scope);heatmap(out,sums['A_primary']/n,cs,names,n,scope)
    return {'scope':scope,'scenario_count':n,'primary_evaluations':int(p.size),'baseline_evaluations':int(baseline.size),'scenario_ids':ids,
            'distance_statistics':stats,'sensitivity':sensitivity,'verification':proof},rankings


@contextlib.contextmanager
def no_network():
    def refuse(*args,**kwargs):raise RuntimeError('Offline analysis forbids all network connections')
    with patch.object(socket.socket,'connect',refuse),patch.object(socket,'create_connection',refuse):yield


def validated_output(output):
    """Only this new supplement directory or paths outside the repo are writable."""
    root = Path(__file__).resolve().parents[1]
    output = Path(output).resolve()
    allowed = (root / DEFAULT_OUT).resolve()
    if output.is_relative_to(root) and output != allowed:
        raise ValueError('Refusing to overwrite existing repository artifacts; use the dedicated supplement or an external directory')
    # An ancestor of the repo would also include protected scientific artifacts.
    if root.is_relative_to(output):
        raise ValueError('Output must not contain the repository')
    return output


def analyze(output=DEFAULT_OUT):
    output=validated_output(output);output.mkdir(parents=True,exist_ok=True)
    config=Path('configs/granite-exploratory-approved.json');m=json.loads(config.read_text());assert digest(m)==RID
    assert all(sha(p)==h for p,h in m['file_sha256'].items())
    before={p:sha(p) for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p and not Path(p).resolve().is_relative_to(output)}
    ids,cs,p,base,rawproof=load_records(m);mask=complete_mask(p,base)
    assert len(ids)==240 and mask.sum()==239 and [s for s,ok in zip(ids,mask) if not ok]==['29912']
    names={c:m['constitutions'][c]['title'] for c in cs}
    official=Path('results/granite-exploratory/cumulative-through-0011');official_ids=[s for b in m['batches'][:11] for s in b['scenario_ids']]
    assert ids[:220]==official_ids and np.isfinite(p[:,:,:220]).all()
    a220,r220=export_scope(output/'official-220-reconstruction',p[:,:,:220],base[:,:220],official_ids,cs,names,'Independent reconstruction of official completed-prefix analysis')
    comparisons={}
    for name in [f'distances-{m}-{mode}-l1.csv' for m in METRICS for mode in ['summed','normalized']]+['probabilities-counterbalanced.csv']+[f'probabilities-{c}.csv' for c in CONDITIONS]:
        rows,cols,committed=read_matrix(official/name);r2,c2,computed=read_matrix(output/'official-220-reconstruction'/name)
        assert rows==r2 and cols==c2 and np.array_equal(committed,computed),f'Official discrepancy: {name}'
        comparisons[name]={'exact_float_equality':True,'CSV_byte_equality':(official/name).read_bytes()==(output/'official-220-reconstruction'/name).read_bytes(),'maximum_difference':float(np.max(np.abs(committed-computed)))}
    selected=[s for s,ok in zip(ids,mask) if ok]
    a239,r239=export_scope(output,p[:,:,mask],base[:,mask],selected,cs,names,'SUPPLEMENTARY complete-case analysis; not completed Batch 12 or revised official experiment')
    expected_rows=[]
    for scope,ranks in [('official_220',r220),('supplementary_239',r239)]:
        for a,b,expectation in PAIRS:
            entry={'scope':scope,'constitution_a':a,'constitution_a_name':names[a],'constitution_b':b,'constitution_b_name':names[b],'illustrative_expectation':expectation}
            for metric,rows in ranks.items():
                row=next(r for r in rows if {r['constitution_a'],r['constitution_b']}=={a,b})
                entry[metric+'_distance']=row['normalized_distance'];entry[metric+'_rank_closest_first']=row['rank_closest_first']
            expected_rows.append(entry)
    table(output/'qualitative-expectations.csv',expected_rows)
    text='# Four illustrative expectations: both scopes, all three metrics\n\nRanks are closest-first among 276 unordered pairs, based on unrounded values. Exact ties share the minimum rank. Expectations are qualitative investigator-supplied examples, not a preregistered benchmark. All four are reported; support is mixed.\n\n'
    for scope in ['official_220','supplementary_239']:
        text+=f'## {scope}\n\n| Pair | Expectation | A (rank) | B (rank) | C (rank) |\n|---|---|---:|---:|---:|\n'
        for r in expected_rows:
            if r['scope']==scope:text+='| '+r['constitution_a_name']+' – '+r['constitution_b_name']+' | '+r['illustrative_expectation']+' | '+' | '.join(f"{r[m+'_distance']:.10f} ({r[m+'_rank_closest_first']}/276)" for m in METRICS)+' |\n'
        text+='\n'
    (output/'qualitative-expectations.md').write_text(text.rstrip()+'\n')
    # Targets are verification-only: never used in selecting data or calculating matrices.
    supplied=[(.0585908781,68),(.0839813601,238),(.0621819200,96),(.0712862406,170)]
    checks=[]
    for r,(value,rank) in zip([r for r in expected_rows if r['scope']=='supplementary_239'],supplied):
        diff=abs(r['A_primary_distance']-value)
        checks.append({'pair':[r['constitution_a'],r['constitution_b']],'computed':r['A_primary_distance'],'supplied_approximation':value,'absolute_difference':diff,'computed_rank':r['A_primary_rank_closest_first'],'supplied_rank':rank,'matches':diff<1e-9 and r['A_primary_rank_closest_first']==rank})
    assert all(c['matches'] for c in checks),'Investigator target disagreement; investigate rather than substitute'
    assert abs(a239['distance_statistics']['A_primary']['mean_normalized']-.0693324511)<1e-9
    assert all(sha(p)==h for p,h in before.items()),'An existing tracked artifact changed during analysis'
    inputs={str(config):sha(config),**rawproof['source_archives_sha256']}
    manifest={'analysis':'SUPPLEMENTARY_COMPLETE_CASE_239','scientific_run_id':RID,'official_scope_unchanged':220,'supplementary_scenario_count':239,'scenario_ids':selected,
              'excluded_scenario_ids':['29912'],'exclusion_reason':'One genuine primary label-distribution measurement is missing: Ubuntu × 29912 labels_swapped. Exclude this scenario for every constitution/condition and baseline in this supplementary common-grid calculation.',
              'not_a_completed_batch12':True,'not_a_revision_to_official_experiment':True,'selection_not_human_certification':True,'no_imputation':True,
              'constitution_names':names,'input_sha256':inputs,'frozen_input_and_source_sha256':m['file_sha256'],'script_sha256':sha(__file__),
              'python':platform.python_version(),'packages':{x:importlib.metadata.version(x) for x in ['numpy','scipy','matplotlib']},'network_access_forbidden_during_analysis':True,'inference_API_calls':0,
              'rank_convention':'Ascending unrounded normalized distances among 276 unordered pairs; exact ties share minimum rank. CSV also supplies maximum tied rank and deterministic ID-tiebreak ordinal.'}
    (output/'analysis-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    formulas={'semantic_probability':'sigmoid(logp1-logp0), or sigmoid(logp0-logp1) for swapped labels',
              'q':'mean of the four semantic probabilities for each constitution-scenario pair',
              'A_normalized':'mean_s abs(q[c,s]-q[d,s])',
              'B_normalized':'mean_k mean_s abs(p[k,c,s]-p[k,d,s])',
              'C_normalized':'mean_s abs(p[canonical,c,s]-p[canonical,d,s])',
              'summed_L1':'N times the corresponding normalized value; L1 of scalar action-probability vectors, not full two-component PMF L1',
              'binary_total_variation':'TV(Bernoulli(p), Bernoulli(q)) = abs(p-q); full PMF L1 = 2*TV'}
    report={'formulas':formulas,'status':'PASS','official_220':a220,'supplementary_239':a239,'official_export_comparisons':comparisons,'source_record_verification':rawproof,
            'supplied_targets_verification_only':checks,'mean_A_target_match':True,'all_preexisting_tracked_files_unchanged':True,'network_calls':0,'inference_API_calls':0,
            'scientific_warning':'Complete-case availability is not a randomized selection policy; scenario 29912 remains in the frozen experiment and its 95 valid primary/four baseline measurements are preserved, but excluded from this supplement. Full 1,336-scenario experiment incomplete; Batch 12 stays stopped.'}
    (output/'verification-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    overview=f'''# Supplementary 239-scenario complete-case analysis (offline only)\n\nThis is **not** completed Batch 12 and **not** a revision to the official 220-scenario analysis or frozen experiment. Dilemma **29912** is excluded for all constitutions and conditions because Ubuntu × 29912 × labels_swapped has no genuine probability. No value is imputed. The other 95 valid primary measurements and four baselines for that dilemma remain in their original archives.\n\nThe analysis independently reconstructs every value from raw label logs and exact frozen requests; its official 220 reconstruction agrees exactly with all committed probability and A/B/C CSV values. See [verification](verification-report.json) and [manifest with exact 239 IDs](analysis-manifest.json). The common grid has 24 constitutions × 239 scenarios × four conditions, plus matching baselines.\n\n- [Full human-readable primary table](primary-distance-table.md) · [accessible standalone HTML](primary-distance-table.html)\n- [Primary CSV](distances-A_primary-normalized-l1.csv) · [SVG heatmap](primary-distance-heatmap.svg) · [PNG](primary-distance-heatmap.png) · [PDF](primary-distance-heatmap.pdf)\n- [Full constitution names](constitutions.csv) · [All four expectations, A/B/C in both scopes](qualitative-expectations.md)\n- [Official 220 independent reconstruction](official-220-reconstruction/) · [Original official exports](../cumulative-through-0011/)\n\nPrimary A compares four-condition averaged semantic probabilities; B averages the four condition-specific distances; C uses canonical alone. Normalized distances divide summed-L1 by 239 (or 220 for the separately reconstructed official scope). These are mean binary total variation, not full two-component distribution L1 (which is twice TV).\n\nReproduce from repository root: `PYTHONPATH=src .venv/bin/python scripts/analyze_granite_research_supplement.py --output /tmp/granite-research-reproduction`. This script has no API client and actively blocks network connections. It never opens a ledger, changes inputs, authorizes tasks, or dispatches inference. Existing source measurements and official outputs are hash-checked unchanged.\n\n![Supplementary primary distance heatmap with full constitution names](primary-distance-heatmap.svg)\n'''
    (output/'README.md').write_text(overview)
    assert all(sha(p)==h for p,h in before.items()),'An existing tracked artifact changed during analysis'
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=DEFAULT_OUT);args=parser.parse_args()
    with no_network():report=analyze(args.output)
    print(json.dumps({'status':report['status'],'official_scenarios':220,'supplementary_scenarios':239,'supplementary_statistics':report['supplementary_239']['distance_statistics'],'targets_verified':True,'inference_API_calls':0},indent=2))
