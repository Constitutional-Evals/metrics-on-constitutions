# Offline engineering and recovery (Batches 9–11)

The frozen scientific manifest, dispatcher, inputs, prompt renderer, probability
extraction and run ID are unchanged. Only nonfrozen offline tooling changes.

## Exact recovery and retention

The initial audit compared every completed evaluation and physical attempt in all
eight batches with archived evidence, checked SQLite integrity and frozen hashes,
and preserved the original Batch 3 failure/recovery. Initial 66 tests passed.
The latest Batch 8 backup matched the authoritative database across all tables,
schema, run specification, settings, stages, states, attempts and spending. An
actual isolated restoration was opened read-only and checked before retention.

`granite_backup.py` retains exact byte snapshots in content-addressed gzip objects.
Seventeen historical filenames map to ten unique objects; seven snapshots were
byte-identical duplicates. Every snapshot was decompressed to an isolated scratch
SQLite file, SHA-256 checked against its source, integrity-checked and compared
across all tables before its redundant uncompressed copy was removed. Historical
metadata and source checksums are not rewritten. `.sqlite.recovery.json` sidecars
map retired original names to exact recoverable objects; keep every sidecar and
object. The migration report contains their checksums and table fingerprints.

Before a new stage, reuse and restore-verify the predecessor backup, comparing its
complete logical contents with a consistent SQLite backup of the active ledger.
Do not generate another permanent before-stage full copy. After a completed stage,
SQLite's backup API makes a consistent temporary snapshot; store a gzip stream of
changed 64-KiB blocks against the verified predecessor, including original size,
source/base/archive hashes. Restore to an isolated SQLite copy, check exact bytes,
integrity and all table fingerprints, then retire the temporary full snapshot.
All failed-attempt records and conservative charges remain in each restored file.
The measured real Batch 7→8 delta is 24,237,193 bytes instead of a 650,342,400-byte
full-size copy. Regression tests cover chained recovery and archive corruption.
Never delete a base object needed by a delta, or overwrite the authoritative DB.

To inspect/recover **to a new isolated path**, with no API request:

```python
import json
from pathlib import Path
from granite_backup import restore_to, inventory
from constitution_distance.local import file_hash
r = json.loads(Path(ORIGINAL_BACKUP_PATH + '.recovery.json').read_text())
assert file_hash(r['archive_path']) == r['archive_sha256']
restore_to(r['archive_path'], NEW_SCRATCH_SQLITE_PATH)
assert file_hash(NEW_SCRATCH_SQLITE_PATH) == r['source_sha256']
assert inventory(NEW_SCRATCH_SQLITE_PATH) == r['all_tables']
```

Run with `PYTHONPATH=src:scripts .venv/bin/python`. Recovery must not overwrite an
active authoritative ledger. Review the recovered identity, accounting and task
states before any separately authorized resumption. Curated batch preservation
manifests now reference compressed recovery metadata as well as original SHA-256.

The working directory and backup directory are on the **same volume**. No approved
off-volume ledger destination is configured. The existing GitHub remote preserves
source, inputs, curated raw evidence and hashes, but deliberately excludes SQLite;
it is not a disaster-recovery backup of authoritative accounting. Do not upload a
ledger to GitHub or provision storage without further authorization.

## Capacity and gates

See `engineering-0009-0011/storage-forecast.json` for measured before/after sizes,
component assumptions and the conservative 9–11 peak. Require 2 GB free beyond
projected persistent growth, two full temporary SQLite copies and 1 GB additional
WAL/sort/analysis allowance. Recheck at every stage. The authorized group fits.
Lossless compression/deduplication reclaimed about 5.08 GB. Incremental snapshots
replace quadratic accumulation of full-size backups with observed incremental
storage, while preserving all exact checkpoints.

A generous end-of-experiment bound exceeds current volume capacity. This group
is safe; that is **not** a guarantee for all 59 remaining batches. Future groups
must repeat the gate. Before it fails, further verified compaction of redundant
raw/curated archives or an approved larger/off-volume destination is required.
No such extra service or later inference is authorized here. Forecasts include
Git/curated growth, raw archives, ledger growth, compressed deltas and scratch.

## Full-export completion fix

Scientific completion requires every frozen science and scheduled canary identity
valid, plus all registered resume canaries valid, and no reserved/in-flight work.
Unknown external charges on *settled* historical failures do not imply missing
science: verify their complete conservative reservation remains charged and their
finish timestamps exist; disclose counts and conservative charges separately.
No original attempt, charge, state, request or probability is altered. Nine new
completion regressions cover unknown-cost failure followed by a valid retry,
reserved/inflight work, missing/invalid science, missing canaries and undercharged
or unsettled unknown billing. The actual incomplete full experiment still cannot
export as complete. Existing Batch 1 and 8 probability and A/B/C CSVs were
recomputed into scratch: all 11 per batch are byte-identical to prior outputs.

Offline cumulative/diagnostic/disjoint CLI entry points accept completed later
prefixes. Prefix scenario counts derive from the frozen schedule (including the
short final batch). They do not dispatch inference or authorize any batch.

Offline numerical versions are recorded in
`results/granite-exploratory/engineering-0009-0011/offline-environment.json`:
Python 3.12.14, NumPy 2.2.5, SciPy 1.15.3, Matplotlib 3.10.3. No inference
package/environment changes were made. Tests use the standard-library unittest
runner: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q`.
