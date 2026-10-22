"""Offline extension of the resumption audit covering adaptive resume canaries.

No API client or dispatcher is called. Existing ledger and archived evidence
must be present. Before/after snapshots include every previously valid row.
"""
import argparse
import gzip
import json
from pathlib import Path

import preflight_granite_resumption as prior
from constitution_distance.exploratory import resume_canary_items

original_snapshot = prior.snapshot
original_canaries = prior.canary_items


def snapshot(db, root, manifest, batch):
    path = Path(f'results/granite-exploratory/batch-{batch:04d}/responses.jsonl.gz')
    records = list(map(json.loads, gzip.open(path, 'rt')))
    extras = []
    for record in records:
        pair = tuple(record['item']['pair'])
        if record['item']['kind'] == 'canary' and '-resume' in pair[1]:
            ordinal = int(pair[1].split('-')[1].removeprefix('resume'))
            expected = next(i for i in resume_canary_items(manifest, batch, ordinal)
                            if tuple(i['pair']) == pair)
            assert record['request'] == expected['request']
            assert record['item']['expected'] == expected['expected']
            extras.append(expected)
    assert len({tuple(r['item']['pair']) for r in records}) == len(records)
    # Reuse all original checkpoint, request, attempt, cap and file checks;
    # additionally visit adaptive QC once, alongside the first scheduled round.
    prior.canary_items = lambda m, b, r: original_canaries(m, b, r) + (extras if r == 0 else [])
    try:
        result = original_snapshot(db, root, manifest, batch)
    finally:
        prior.canary_items = original_canaries
    assert sum(result['valid'].values()) == len(records)
    return result


prior.snapshot = snapshot

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--batch', type=int, required=True)
    p.add_argument('--after', action='store_true')
    a = p.parse_args()
    assert 3 <= a.batch <= 5, 'This authorization group contains only batches 3–5'
    report = prior.audit(a.batch, a.after)
    if a.batch == 3 and not a.after:
        assert report['spending_preserved_usd'] == 0.206581896
        before = json.loads(Path('results/granite-exploratory/batch-0003/resumption-preflight.json').read_text())
        assert {k: sum(v['valid'][k] for v in before['prior_stages'].values())
                for k in ['primary', 'baseline', 'canary']} == {'primary': 3840, 'baseline': 160, 'canary': 66}
    print(json.dumps(report, indent=2))
