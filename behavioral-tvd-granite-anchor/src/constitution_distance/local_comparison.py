"""Explicit cross-configuration comparisons; never merges checkpoints or launches inference."""
import json,sqlite3,statistics
from pathlib import Path
from .core import digest
from .local import Checkpoint


def compare_runs(reference,candidate):
    def read(path):
        path=Path(path);db=sqlite3.connect(path/'checkpoint.sqlite');spec=json.loads(db.execute('SELECT body FROM config').fetchone()[0]);db.close()
        if path.name!=digest(spec):raise ValueError('Run directory/configuration mismatch')
        cp=Checkpoint(path.parent,spec)
        try:
            expected=len(spec['inputs'])*spec['config']['repeats']*len(spec['config']['planned_sessions'])
            if len(cp.records)!=expected:raise ValueError('Cross-configuration comparison requires complete planned measurements')
            groups={}
            for r in cp.records.values():groups.setdefault(r['item_id'],[]).append(r)
            return spec,groups
        finally:cp.close()
    a,aa=read(reference);b,bb=read(candidate)
    if a['inputs']!=b['inputs'] or a['prompt_hashes']!=b['prompt_hashes']:raise ValueError('Different prompts or tokenization')
    for key in ['revision','tokenizer_revision']:
        if a['lock'][key]!=b['lock'][key]:raise ValueError('Different artifact revision')
    for key in ['model','tokenizer']:
        if a['lock'][key]['files']!=b['lock'][key]['files']:raise ValueError('Different artifact checksums')
    rows=[]
    for key in sorted(aa):
        pa=[r['probabilities']['p1_conditional'] for r in aa[key]];pb=[r['probabilities']['p1_conditional'] for r in bb[key]]
        la=[r['probabilities']['log_odds'] for r in aa[key]];lb=[r['probabilities']['log_odds'] for r in bb[key]]
        rows.append({'id':key,'reference_mean_p':statistics.mean(pa),'candidate_mean_p':statistics.mean(pb),'mean_probability_difference':abs(statistics.mean(pa)-statistics.mean(pb)),
            'mean_log_odds_difference':abs(statistics.mean(la)-statistics.mean(lb)),
            'reference_probability_range':max(pa)-min(pa),'candidate_probability_range':max(pb)-min(pb)})
    return {'reference':str(reference),'candidate':str(candidate),'reference_config':a['config'],'candidate_config':b['config'],'pairs':rows,
        'maximum_mean_probability_difference':max(r['mean_probability_difference'] for r in rows),'maximum_mean_log_odds_difference':max(r['mean_log_odds_difference'] for r in rows),
        'warning':'Between-configuration comparison, not within-configuration reproducibility. Reference and candidate remain separate runs.'}
