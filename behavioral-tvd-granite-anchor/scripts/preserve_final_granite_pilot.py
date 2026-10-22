"""Archive this pilot only. No API calls; historical experiments remain untouched."""
import gzip
from collections import Counter
import hashlib
import json
import lzma
import shutil
import sqlite3
from pathlib import Path

from constitution_distance.core import digest

B = Path('/workspace/work/granite-final-pilot')
O = Path('results/granite-final-pilot/evidence')


def packed(source, destination):
    with Path(source).open('rb') as src, Path(destination).open('wb') as dst:
        with gzip.GzipFile(filename='', mode='wb', fileobj=dst, mtime=0) as z:
            shutil.copyfileobj(src, z)


def main():
    O.mkdir(parents=True, exist_ok=True)
    preservation = json.loads((B / 'preservation.json').read_text())
    changed = [p for p, h in preservation['tracked_files'].items()
               if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h]
    if changed:
        raise ValueError('Historical tracked files changed: ' + repr(changed))
    shutil.copyfile(B / 'preservation.json', O / 'preservation.json')
    for name in ['design.json', 'design-v2.json', 'design-v3.json', 'design-v4.json', 'design-v5.json']:
        source = B / name
        design = json.loads(source.read_text())
        folder = B / digest(design)
        compressed = O / (name + '.xz')
        if compressed.exists():
            if lzma.open(compressed,'rb').read() != source.read_bytes():
                raise ValueError('Immutable archived configuration mismatch')
        else:
            with source.open('rb') as src, lzma.open(compressed,'wb') as dst:
                shutil.copyfileobj(src,dst)
        (O / (name + '.gz')).unlink(missing_ok=True)
        if name == 'design-v5.json':
            packed(folder / 'responses.jsonl', O / 'raw-final-responses.jsonl.gz')
        for snapshot in list(folder.glob('execution-*.json')) + list(folder.glob('STOP.json')):
            packed(snapshot, O / (folder.name[:12] + '-' + snapshot.name + '.gz'))
    for folder in B.iterdir():
        if folder.is_dir() and (folder / 'configuration.json').exists():
            design = json.loads((folder / 'configuration.json').read_text())
            if design.get('kind') == 'canary' or 'canary' in str(design.get('purpose', '')):
                packed(folder / 'configuration.json', O / 'canary-configuration.json.gz')
                packed(folder / 'responses.jsonl', O / 'canary-responses.jsonl.gz')
    # Also identify the canary robustly by its 12 expected measurements.
    for folder in B.iterdir():
        if folder.is_dir() and (folder / 'configuration.json').exists():
            design = json.loads((folder / 'configuration.json').read_text())
            if len(design.get('items', [])) == 12:
                packed(folder / 'configuration.json', O / 'canary-configuration.json.gz')
                packed(folder / 'responses.jsonl', O / 'canary-responses.jsonl.gz')
    for name in ['predictions-before-inference.json', 'resume-authorization.json',
                 'resume-review-plan.json', 'second-resume-review-plan.json',
                 'second-resume-authorization.json',
                 'third-resume-review-plan.json', 'third-resume-authorization.json',
                 'all-tests.log', 'live.log', 'live-v2.log', 'live-v3.log', 'live-v4.log', 'live-v5.log']:
        packed(B / name, O / (name + '.gz'))
    for version in ['implementation-v1', 'implementation-v2']:
        shutil.copytree(B / version, O / version, dirs_exist_ok=True)
    db = sqlite3.connect(B / 'budget.sqlite')
    rows = [dict(zip([d[0] for d in cursor.description], row))
            for cursor in [db.execute('SELECT * FROM attempts ORDER BY started,id')]
            for row in cursor]
    with (O / 'attempts.jsonl.gz').open('wb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as z:
            for row in rows:
                z.write((json.dumps(row, ensure_ascii=False) + '\n').encode())
    charged = sum(r['charged'] for r in rows) / 1e9
    actual = sum(r['charged'] for r in rows if r['actual_cost'] is not None) / 1e9
    held = sum(r['reserve'] for r in rows if r['state'] == 'reserved') / 1e9
    usage = [json.loads(r['response']).get('usage',{}) for r in rows if r['response']]
    (O / 'budget-summary.json').write_text(json.dumps({
        'cap_usd': .75, 'attempts': len(rows), 'actual_spending_usd': actual,
        'conservative_spending_usd': charged, 'outstanding_reservations_usd': held,
        'unknown_billing_attempts': sum(r['actual_cost'] is None for r in rows),
        'http_status_counts': dict(Counter(str(r['http_status']) for r in rows)),
        'attempt_state_counts': dict(Counter(r['state'] for r in rows)),
        'invalid_errors': dict(Counter(r['error'] for r in rows if r['state']=='invalid')),
        'prompt_tokens_all_physical_attempts': sum(u.get('prompt_tokens',0) for u in usage),
        'completion_tokens_all_physical_attempts': sum(u.get('completion_tokens',0) for u in usage),
        'note': 'Imported valid records are not new attempts or new charges.'}, indent=2) + '\n')
    backup = Path('/workspace/backups/granite-final-pilot')
    backup.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(backup / 'budget.sqlite')
    db.backup(target)
    target.close()
    db.close()
    print(json.dumps({'preserved_historical_files': len(preservation['tracked_files']),
                      'attempts': len(rows), 'charged_usd': charged, 'held_usd': held}))


if __name__ == '__main__':
    main()
