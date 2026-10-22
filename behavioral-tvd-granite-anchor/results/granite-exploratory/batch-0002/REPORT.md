# Batch 2 complete; cross-task resumption verified

Only Batch 2 was executed under the unchanged protocol from commit a8c1a66,
run `03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.
Batch 3 and later batches remain unauthorized and unstarted.

The original SQLite ledger passed read-only integrity, manifest, source/input
hash, checkpoint and spending-history checks before any API request. It was
not replaced or reset. Batch 1 retained 1,920 primary, 80 baseline and 30 canary
records as valid, with its full 2,031-attempt history and $0.099496116 spending.
A before-stage ledger backup was made. After Batch 2, all Batch 1 rows and files,
and all 397 pre-existing tracked files, matched their before-stage fingerprints.
The approved $10 global cap and all original charges remain intact.

## Batch results

| Quantity | Batch 2 |
|---|---:|
| New frozen scenarios | 20 |
| Valid primary evaluations | 1,920 |
| Valid baselines | 80 |
| Valid scheduled canaries | 30 |
| Additional resume canaries | 6 |
| Total valid records | 2,036 |
| Physical primary attempts | 1,923 / 2,000 ceiling |
| Total physical attempts | 2,039 |
| Failed transport attempts | 3, all recovered |
| Missing scientific/QC tasks in this batch | 0 |
| Confirmed response charges | **$0.099736308** |
| Conservative stage spending | **$0.107085780 / $1 cap** |
| Held reservations | $0 |
| Active dispatch time, both invocations | **498.72 seconds** |
| Wall time, including stop/reconciliation | 666.55 seconds |
| Valid evaluations / active second | **4.082** |

There was one HTTP 502 and two truncated-response `IncompleteRead` failures.
The frozen dispatcher stopped at 2,004 valid records, leaving 26 missing tasks.
After its exit, the two unresolved reservations were manually settled through
the existing ledger operation: entire original reserves became conservative
charges, no actual cost or HTTP status was invented, and the permitted remaining
attempts were retained. The HTTP 502 already carried the same conservative
charge. Total unknown-cost charges are **$0.007349472**. Exact actual billing for
those three attempts remains unknown; conservative accounting is not a claim
that the provider actually charged that amount.

The unchanged runner resumed only the 26 missing tasks, first issuing six fresh
canaries as required by its frozen resume policy. All tasks then succeeded.
Every one of the 2,004 pre-interruption valid attempts remains byte-for-byte
equivalent in the durable attempt history and retains its original response;
none was reissued. No task used more than two attempts, below the lifetime
three-attempt limit. Source, parameters, provider and run ID did not change.
The initial stop evidence and conservative settlement journal are preserved.

All 36 canaries matched reference conditional probabilities, raw label logs and
log odds exactly. All 2,036 valid responses reported the requested Granite model
and Cloudflare. Both answer-token logs were finite in every valid record;
minimum binary answer-token mass was 0.998252, with no sampled-format violations.
The observed 0.125 log-odds grid persists. Returned usage totals are 5,853,428
input tokens and 2,036 output tokens; usage absent from the three failed calls is
not invented or silently counted as zero billed usage.

## Batch-specific geometry

All matrices below use **this batch's 20 scenarios only**. They are not final
1,336-scenario results. Mean normalized distance over the 276 constitution pairs:

| Metric | Mean normalized distance |
|---|---:|
| A: distance between four-condition mean probability vectors | 0.082262 |
| B: mean of four condition-specific distances | 0.098310 |
| C: canonical-only distance | 0.102897 |

Each has a separate summed-L1 export, equal to 20 times its normalized version.
All are symmetric, nonnegative and have zero diagonals. B >= A was checked;
their maximum normalized gap was 0.043954. Independent recomputation differed
by at most 4.44×10⁻¹⁶. The 2,030 scheduled request/message hashes matched the
frozen plan; the six adaptive QC hashes matched its explicit resume-task rule.

Canonical versus A pair-distance Spearman correlation was 0.7994. Mean absolute
label-mapping effect was 0.3315; action-line order effect was 0.1863. These are
descriptive Granite-conditioned behaviors, not philosophical distances or
evidence of perfect ethical implementation. Probability vectors, baselines,
baseline shifts, A/B/C matrices, rankings, scenario contributions, subsampling
diagnostics and heatmaps are exported separately.

All 63 automated tests passed. Frozen dispatch source remained unchanged; new
code performs offline resumption auditing, cumulative reporting and verification
of adaptive QC. The legacy report's latest-invocation timing is preserved in
`batch-report-latest-invocation.json`; `batch-report.json` correctly aggregates
both dispatch invocations and separates scheduled from adaptive QC.

## Cumulative progress and next authorization

Two completed batches cover 40 scenarios: **3,840 primary evaluations, 160
baselines and 66 canaries**, or **4,066 valid records** from **4,070 attempts**.
There are four historical failed attempts: Batch 1's known-cost null-logprob
response and Batch 2's three uncertain-cost transport failures.

Confirmed cumulative response charges are **$0.199232424**; conservative budget
accounting is **$0.206581896 of $10**, with no held reservations. The three actual
billing outcomes remain to be reconciled before final financial closeout; their
maximum charges already reduce available budget.

Remaining are **124,416 primary evaluations, 5,184 baselines and 1,950 scheduled
canaries across 65 batches**. The extra six completed resume canaries do not
replace future scheduled QC. Using cumulative throughput and conservative
failed-attempt charges, projected remaining cost is **$6.68**, or **$6.89 total**,
and remaining active inference time is **9.03 hours**. Allow roughly ±20% plus
setup, approval delays and future recovery overhead; these are not guarantees.

A small explicit authorization for **Batches 3–5 sequentially** is reasonable:
approximately 25 minutes of active work and about $0.30–$0.32 at observed rates.
Retain the existing $1 stage caps, global $10 cap, concurrency three and all QC/
retry gates, and stop the group on any exception needing review/reconciliation.
This recommendation authorizes nothing. Execution remains stopped after Batch 2.

Current cumulative report: [`../PROGRESS.md`](../PROGRESS.md).
Raw evidence and consistent ledger backups exist independently outside Git;
credentials and the authoritative ledger are excluded from commits.
