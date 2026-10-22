"""Independently verify exported pilot matrices; no inference or imputation."""
import csv
import json
from pathlib import Path

O = Path('results/granite-final-pilot')
CONDITIONS = ['canonical', 'labels_swapped', 'order_reversed', 'both_reversed']


def read_matrix(path):
    rows = list(csv.reader(path.open()))
    labels = [r[0] for r in rows[1:]]
    return labels, rows[0][1:], [[float(x) for x in r[1:]] for r in rows[1:]]


def main():
    matrices = {}
    max_error = 0.
    for name in CONDITIONS + ['counterbalanced']:
        labels, scenarios, p = read_matrix(O / ('probabilities-' + name + '.csv'))
        assert len(labels) == 24 and len(scenarios) == 20
        assert all(len(v) == 20 and all(0 <= x <= 1 for x in v) for v in p)
        matrices[name] = p
        for form, scale in [('summed', 1), ('mean', 1 / 20)]:
            dl, dc, distances = read_matrix(O / ('distances-' + name + '-' + form + '-l1.csv'))
            assert dl == labels == dc
            for i in range(24):
                assert distances[i][i] == 0
                for j in range(24):
                    expected = sum(abs(x-y) for x, y in zip(p[i], p[j])) * scale
                    error = abs(distances[i][j] - expected)
                    max_error = max(max_error, error)
                    assert error < 1e-12
                    assert distances[i][j] >= 0 and abs(distances[i][j] - distances[j][i]) < 1e-12
    for i in range(24):
        for s in range(20):
            expected = sum(matrices[k][i][s] for k in CONDITIONS) / 4
            assert abs(expected - matrices['counterbalanced'][i][s]) < 1e-12
    rows = list(csv.DictReader((O / 'evaluations.csv').open()))
    assert len(rows) == 4336
    assert len({(r['kind'], r['constitution'], r['scenario'], r['condition'], r['replica']) for r in rows}) == 4336
    cost = sum(float(r['cost']) for r in rows)
    summary = {'status': 'PASS', 'probability_matrices': 5, 'distance_matrices': 10,
               'main_evaluations': 3840, 'all_valid_evaluations': 4336,
               'missing': 0, 'maximum_independent_distance_error': max_error,
               'valid_final_record_cost_usd_excluding_canaries_and_invalid_attempts': cost,
               'checks': ['dimensions', 'probability ranges', 'no missing', 'unique slots',
                          'symmetry', 'zero diagonal', 'nonnegative', 'sum/mean scaling',
                          'independently recomputed L1', 'counterbalanced probability averaging']}
    (O / 'independent-verification.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
