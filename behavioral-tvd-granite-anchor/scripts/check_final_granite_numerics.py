"""Read-only numerical/identity audit of the completed isolated pilot."""
import collections
import csv
import json
import math
import os
from pathlib import Path

import numpy as np
from constitution_distance.core import digest

B = Path('/workspace/work/granite-final-pilot')
O = Path('results/granite-final-pilot')


def main():
    spec = json.loads(Path(os.environ.get('GRANITE_DESIGN_FILE',str(B / 'design-v5.json'))).read_text())
    rows = [json.loads(s) for s in (B / digest(spec) / 'responses.jsonl').read_text().splitlines()]
    assert len(rows) <= 4336
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row['request_hash']].append(row)
    columns = ['kind','constitution_id','scenario_id','condition','replica',
               'p_to_do','logp0','logp1','p0','p1','p1_conditional','binary_mass',
               'sampled_output','format_compliant','request_hash','prompt_hash',
               'model','provider','prompt_tokens','completion_tokens','cost']
    with (O/'probability-audit-evaluations.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');writer.writeheader()
        for row in rows:
            item=row['item'];result=row['result'];response=row['response'];usage=response['usage']
            record={k:item[k] for k in columns[:5]}
            record.update({k:result[k] for k in columns[5:14]})
            record.update({k:row[k] for k in ['request_hash','prompt_hash']})
            record.update({k:response[k] for k in ['model','provider']})
            record.update({k:usage[k] for k in ['prompt_tokens','completion_tokens','cost']})
            writer.writerow(record)
    repeats = [v for v in groups.values() if len(v) > 1]
    masses = [r['result']['binary_mass'] for r in rows]
    differences = {k: max(max(v['result'][k] for v in g) - min(v['result'][k] for v in g)
                          for g in repeats)
                   for k in ['logp0', 'logp1', 'p1_conditional', 'log_odds']}
    odds = [r['result']['log_odds'] for r in rows]
    # A lattice in differences is more diagnostic than printed decimal lengths.
    quantization = {str(step): float(np.mean([abs(x - step * round(x / step)) < 1e-5
                                            for x in odds]))
                    for step in [.125, .0625, .03125, .015625]}
    result = {
        'valid_records': len(rows), 'missing_records': 4336-len(rows),
        'status': 'complete' if len(rows)==4336 else 'stopped_incomplete',
        'distinct_request_hashes': len(groups),
        'repeated_identical_request_groups': len(repeats),
        'repeated_groups_with_p1_between_0.1_and_0.9': sum(.1 <= g[0]['result']['p1_conditional'] <= .9 for g in repeats),
        'repeated_groups_with_p1_between_0.4_and_0.6': sum(.4 <= g[0]['result']['p1_conditional'] <= .6 for g in repeats),
        'maximum_repeated_differences': differences,
        'model_counts': dict(collections.Counter(r['response']['model'] for r in rows)),
        'provider_counts': dict(collections.Counter(r['response']['provider'] for r in rows)),
        'sampled_format_noncompliant': sum(not r['result']['format_compliant'] for r in rows),
        'sampled_tokens': dict(collections.Counter(r['result']['sampled_output'] for r in rows)),
        'both_finite_label_logs': all(math.isfinite(r['result'][k]) for r in rows for k in ['logp0', 'logp1']),
        'binary_mass_quantiles': dict(zip(['min', 'p01', 'p05', 'p25', 'median', 'p75', 'p95', 'p99', 'max'],
                                        np.quantile(masses, [0, .01, .05, .25, .5, .75, .95, .99, 1]).tolist())),
        'binary_mass_below_0.5': sum(x < .5 for x in masses),
        'binary_mass_below_0.9': sum(x < .9 for x in masses),
        'binary_mass_below_0.99': sum(x < .99 for x in masses),
        'log_odds_lattice_fractions_tolerance_1e-5': quantization,
        'interpretation': 'Lattice structure suggests finite-precision computation; decimal display is not numerical accuracy. No evidence of a hard clipping floor is not proof of absence. Conditional probabilities are forced-choice preferences, not unconditional action confidence.',
    }
    (O / 'numerical-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
