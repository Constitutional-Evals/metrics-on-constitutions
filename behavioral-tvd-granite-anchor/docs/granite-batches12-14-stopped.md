# Granite Batches 12–14: group stopped during Batch 12

**No new batch completed. Batch 12 stopped for manual review. Batches 13 and 14
were never started. No Batch 15 or later authorization exists. Do not resume or
launch another batch under the historical conditional authorization files.**

The original group authorization required stopping the entire group on a manual-
review error. That condition occurred. No retry, checkpoint reclassification,
replacement ledger, frozen-dispatcher patch or additional inference followed it.
All scientific inputs, settings, templates, run ID and frozen source hashes remain
unchanged from the approved protocol. The latest fully completed batch prefix is
still Batches 1–11 / 220 scenarios; its matrices remain byte-unchanged.

## Preflight and preservation

Started from commit `72ead075ee76cb6a0691828a528084b753c1df58`, branch `work`,
run `03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.
All eleven archived evaluation/attempt histories, original Batch 3 failure and
recovery evidence, frozen manifest/input/source hashes, SQLite integrity, original
$10 budget, expected counts and spending passed the comprehensive preflight.
Both initial and final **77-test suites pass**. The latest ledger backup was
actually restored to an isolated scratch file, SHA-256 checked, opened read-only,
SQLite-integrity checked and compared across every table with the authoritative
state. All required incremental-chain dependencies were verified.

The runtime metadata tool reported network/secret setup as unknown, so readiness
was not assumed. An authenticated, non-inference GET `/api/v1/key` succeeded with
HTTP 200. No key value or response body was printed or saved.

Starting free space was 23.333 GB on a 33.770 GB volume. The three-batch conservative
peak forecast allowed 1.05 GB persistent growth, two temporary full SQLite copies,
1 GB WAL/sort/analysis allowance and a mandatory 2 GB reserve. It projected 18.918 GB
free at peak and passed. Explicit immutable authorizations for 12,13,14 were linked
to the investigator request hash. Operational offline verification scope was
extended to that group; inference code was not changed.

The post-stop preservation audit verified that every prior valid evaluation,
failed attempt, conservative charge and previously tracked scientific output was
unchanged. The stopped checkpoint has a new exact-byte incremental backup against
Batch 11, independently restored and compared across all tables again. It includes
the invalid response and all charges. No dependencies or historical evidence were
deleted. Raw evidence is archived outside Git; curated compressed raw responses,
attempts, configurations, checksums and partial outputs are versioned.

## Incident

| Field | Observed value |
|---|---|
| Constitution | Neo-Aristotelian virtue ethics |
| Dilemma | 29912 |
| Condition | canonical (replica 0) |
| Attempt | `9b4128fc0dcb469e817b209db3489378` |
| HTTP status | 200 |
| Error inside response | `504`, `Upstream idle timeout exceeded` |
| Frozen validator classification | `Model/provider mismatch` |
| Model/provider/choices/token logs in envelope | absent |
| Actual external billing | unknown |
| Full conservative reservation retained | $0.002449824 |
| Immutable attempt fingerprint | `a13e3481a060d4385bb41f5d60302af89884cf696bb8868faf6b2e938b385527` |

This is an error-only upstream timeout envelope, not evidence that a different
model was actually served. The frozen validator rejects the missing identity;
it was **not** reclassified as automatically retryable. The previously proposed
HTTP 200 error-policy modification remains inactive. All dispatched calls settled
before preservation; no outstanding requests or reservations remain.

## Measurements and costs

| Batch | State | Primary / baseline / canary valid | Confirmed cost | Conservative cost |
|---|---|---:|---:|---:|
| 12 | stopped, incomplete | 1,734 / 74 / 24 | $0.089612009 | $0.092061833 |
| 13 | not started | 0 / 0 / 0 | $0 | $0 |
| 14 | not started | 0 / 0 / 0 | $0 | $0 |

Batch 12 made 1,833 physical attempts: 1,832 valid responses and one failed attempt.
No retries or resume canaries occurred. There are **198 missing scheduled
measurements**: 186 primary (including the failed pair), six baselines and six
final scheduled canaries. Its primary-attempt count is 1,735, below the 2,000 cap.
Stage conservative spending remains below $1; all original safeguards are retained.

All 1,832 valid responses match frozen request/prompt identities and report
`ibm-granite/granite-4.0-h-micro` / `Cloudflare`. Independent reconstruction verified
both genuine literal ASCII token logs, their raw/unconditional/conditional values,
and original semantic `to_do` orientation. Maximum independent probability error
is 2.23e-16. All 24 executed canaries have exactly matching raw logs and stored
conditional probabilities; the independent exp/ratio calculation differs from its
reference by at most 1.12e-16 through floating arithmetic. The unexecuted final six
canaries are explicitly missing. Minimum observed binary mass is 0.998063; all
valid log odds remain on the observed 0.125 grid (tolerance 1e-5).

The four partial condition matrices and their average are exported with blanks,
never zero substitution. There are 186 missing primary condition cells, six missing
baseline condition cells, and 107 counterbalanced cells without all four inputs.
The ordinary complete-batch exporter correctly refuses this grid. **No full
Batch 12 A/B/C matrices or 24×280 cumulative matrix was produced.**

## Cumulative state and unchanged scientific analysis

Cumulative valid counts are **22,854 primary**, **954 baseline** and **366 canary**
(354 scheduled + 12 historical resume checks): **24,174 valid records** from
**24,183 physical attempts**. There are nine historical failed attempts and five
conservatively charged unknown-billing outcomes, including the new timeout.
Confirmed charges total **$1.184580525**; conservative spending is **$1.196829645**
of $10, leaving $8.803170355. Outstanding reservations are zero. The five unknown
outcomes retain $0.012249120 in conservative charges; their true external billing
remains unknown.

There are 235 scenarios with all 100 science measurements: the original 220 plus
15 fully observed scenarios in the stopped stage. Batch 12 is still incomplete;
no new complete-case subset was substituted into the intended analysis. The latest
fully completed-batch cumulative analysis remains **24×220**, with unchanged values:

| Metric | Mean normalized | Min normalized | Max normalized | Mean summed L1 |
|---|---:|---:|---:|---:|
| A | 0.069121160 | 0.039279209 | 0.123529778 | 15.206655212 |
| B | 0.084713945 | 0.050327067 | 0.141745155 | 18.637067809 |
| C | 0.082583371 | 0.038592443 | 0.180344809 | 18.168341576 |

At that unchanged 220-scenario scope, nested 200→220 pair-rank Spearman is 0.996458,
with 23/24 nearest neighbors unchanged; disjoint 110-versus-110 Spearman is 0.799986,
with 13/24 neighbors matching. Mean absolute label/order effects are 0.290042 /
0.169579; mean absolute constitution-to-baseline shift is 0.104741. Existing scenario
contributions remain available for completed batches. These are preliminary
Granite-conditioned behavioral distances, not final-library results or established
philosophical distances. No post-stop inference or methodological changes occurred.

## Performance, storage and next steps

Batch 12 active inference was **563.070 seconds / 9.38 minutes**, yielding
**3.25359 valid responses/s**. Aggregate active inference is **6,673.225 seconds /
111.22 minutes**, **3.62254 valid responses/s**. An additional 111,448 scheduled
evaluations remain: 105,402 primary, 4,390 baseline, 1,656 scheduled QC, plus any
future authorized restart QC/retries. There are 56 unfinished batches including
Batch 12, of which 55 have not started. Estimated remaining inference is **8.55
active hours**, **$5.52** additional cost and **$6.71** total; allow roughly ±20%
variation and task/review overhead. Projections do not authorize dispatch.

After preservation, approximately **23.13 GB** was free before final Git/review
archive overhead, up from neither a reset nor evidence deletion. Measured volume
growth was about **206 MB** at that point. The authoritative DB is 952,602,624 bytes;
the stopped delta archive is 24,056,564 bytes. Recent complete stages grew the
ledger by 77.4–77.6 MB, working raw evidence by about 74.7 MB, and checkpoint deltas
by 24.7–25.7 MB. Backup-chain restoration and source/archive hashes passed.

Using the larger established 350 MB persistent-per-batch bound plus two temporary
full final-ledger copies and 1 GB additional scratch, a **five-batch** group has
5.655 GB additional peak storage demand. It would leave **17.47 GB** free, well
above the 2 GB reserve. Thus storage capacity supports five; this is based on
measured growth and conservative bounds, not a guarantee for all remaining batches.
Local backups remain on the working volume and do not provide independent
volume-loss recovery. No external service was provisioned and no ledger uploaded.

**Recommendation:** first review the exact failed envelope and authorize recovery
of Batch 12 alone under a separate explicit scope, preserving all 1,832 valid
records and the original failed attempt/charge. Do not reclassify or retry it
without that review. After a clean recovery and restored integrity/storage gates,
a five-batch sequential authorization is reasonable. Batches 13–14's historical
conditional files do not override the current group stop. Batch 15+ remains
unauthorized. No further inference is authorized by this report.

Key evidence: `results/granite-exploratory/progress-stopped-batch-0012.json`,
`batch-0012/independent-partial-verification.json`, `batch-0012/attempts.json.gz`,
`batch-0012/stopped-ledger-recovery.json`, `engineering-0012-0014/`, and the explicit
`configs/granite-exploratory-authorizations/groups/batches-0012-0014-stopped.json`.
The original provisional curation report is retained separately; reconciled
accounting excludes historical resume canaries from remaining scheduled QC and
counts stopped Batch12 among unfinished batches. This correction is offline only.
