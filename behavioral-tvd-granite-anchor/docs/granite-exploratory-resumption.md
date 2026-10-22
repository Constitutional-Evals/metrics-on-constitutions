# Cross-task resumption: Batch 2

The investigator authorized **Batch 2 only**, under the unchanged protocol from
commit `a8c1a66`, run
`03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.
This authorization does not include Batch 3 or any later batch. Source code,
model/provider, rendering, inference parameters and scientific metrics remain
unchanged; new code is limited to offline auditing and cumulative reporting.

## Before any API request

The read-only preflight verified the manifest/run hash and all frozen artifact
hashes, then opened the **existing** SQLite file with `mode=ro`. It did not
instantiate a replacement experiment ledger. SQLite integrity was `ok`; the
single registered experiment matched the manifest; the original global cap was
$10; and $0.099496116 of Batch 1 spending remained accounted for.

All 1,920 Batch 1 primary, 80 baseline and 30 canary checkpoints were validated
against their exact frozen requests, request/message hashes, computed
probabilities and committed raw records. All 2,031 prior physical attempts,
including the recovered null-logprob response, matched the committed attempt
archive. There were no in-flight evaluations or held reservations.

The preflight saved SHA-256 fingerprints of every prior evaluation/attempt row,
stage configuration, operational and curated Batch 1 files, and pre-existing
tracked files. It also made a consistent independent before-stage SQLite backup.
The audit record is `results/granite-exploratory/batch-0002/resumption-preflight.json`.
Missing/inconsistent authoritative state would have stopped this procedure
before network access; exports are never used to initialize a fresh spending
ledger and repeat paid evaluations.

## Authorized dispatch

`configs/granite-exploratory-authorizations/batch-0002.json` explicitly authorizes
only Batch 2. It retains the $1 lifetime stage cap, 2,000 physical primary-attempt
ceiling, concurrency three, lifetime retry limit, null-logprob backoff, canary
schedule, exact identity checks, and all existing spending reservations. The
experiment-wide budget is still $10, with Batch 1 charges retained.

Batch 2 uses the next 20 scenario IDs from the frozen global schedule. Their IDs
are recorded in the authorization-associated preflight, are disjoint from Batch
1's IDs, and are not sampled again. The grid contains 1,920 primary tasks, 80
baseline tasks and 30 scheduled canaries. Repeated canaries are deliberately
separate QC tasks; no completed Batch 1 task is reissued.

```bash
PYTHONPATH=src .venv/bin/python scripts/preflight_granite_resumption.py --batch 2
PYTHONPATH=src .venv/bin/python scripts/granite_exploratory.py execute \
  --batch 2 --experiment-budget-usd 10 --stage-budget-usd 1
```

The preflight above is a fresh-next-batch audit, not a command to override an
already partial stage or overwrite its backup. Such a condition requires review.
The frozen runner itself retains its approved idempotent resume behavior and
fresh-QC policy. Existing valid records are skipped; uncertain in-flight charges
remain held until reconciled.

## After dispatch stops

All following commands are offline. Batch-specific analysis uses only its 20
scenarios; full-library export remains blocked until the complete scientific
grid, canary schedule and billing checks pass.

```bash
PYTHONPATH=src .venv/bin/python scripts/analyze_granite_exploratory.py --batch 2
PYTHONPATH=src .venv/bin/python scripts/preserve_granite_exploratory.py --batch 2
PYTHONPATH=src .venv/bin/python scripts/preflight_granite_resumption.py --batch 2 --after
PYTHONPATH=src .venv/bin/python scripts/report_granite_exploratory_progress.py --through-batch 2
PYTHONPATH=src .venv/bin/python scripts/verify_granite_resumed_batch.py --batch 2
```

The postcheck compares original row and file fingerprints rather than hashing
the entire live SQLite file, which legitimately changes when new records are
added. It checks both original paid attempts and their costs/timestamps, not just
the exported probability values. Consistent after-stage SQLite backups and
curated raw evidence are preserved independently outside Git. The authoritative
ledger and credentials are never committed.

Near completion, one HTTP 502 and two `IncompleteRead` transport failures stopped
the frozen dispatcher. The process exited with 2,004 valid checkpoints and 26
missing tasks. The two unsettled reservations were manually settled to `retry`
using the existing ledger operation, after acquiring the exclusive experiment
lock. Their entire original reservations became conservative charges; actual
costs and HTTP statuses were not invented. The HTTP 502 was already charged in
the same conservative way by the frozen runner. Total unknown-cost charges are
$0.007349472, retained against the budget until billing can be reconciled.

The existing runner then resumed only missing tasks within their lifetime retry
limits, first adding six fresh canaries under the frozen resume-QC rule. All
missing tasks succeeded. All 2,004 pre-interruption valid attempts and all Batch
1 rows/files remained unchanged. This was not an inference-code or protocol
change. The stop summary, attempt archive, reconciliation journal and both
dispatch logs are preserved in the Batch 2 evidence.

The original generic export utility reports the latest invocation's duration and
does not distinguish adaptive QC from scheduled QC correctly after resume. Its
raw report is preserved as `batch-report-latest-invocation.json`; the new offline
audit writes corrected aggregate-invocation timing and scheduled-QC counts to
`batch-report.json`. No frozen dispatch source was modified. The independent
matrix audit verifies the six extra QC requests against the manifest's explicit
adaptive-task derivation. Usage absent from failed responses remains missing.

Current cumulative results are in
[`results/granite-exploratory/PROGRESS.md`](../results/granite-exploratory/PROGRESS.md).
The original Batch 1 report remains an unchanged historical snapshot. All
interpretation remains Granite-conditioned exploratory behavior, not established
philosophical distances; the 0.125 log-odds quantization limitation persists.

After successful checks, a small explicitly authorized group of three sequential
batches would be a reasonable next operational step. It must retain all stage
caps and stop/QC gates and stop at the end of that named group. This recommendation
does not itself authorize or start any later batch.
