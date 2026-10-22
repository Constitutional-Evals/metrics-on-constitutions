# Batch 12 reviewed recovery: target succeeded, batch stopped again

**The authorized one-row recovery succeeded. Batch 12 did not complete: a new
substantive timeout triggered the unchanged stop rule. No Batch 13, 14 or later
batch was launched or reactivated. No new invalid checkpoint was reclassified.**

Run ID remains `03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.
Recovery began from commit `4b4e437a08775fdfc23147c4fae91bdb30061bf3`. All scientific
source/input hashes, prompts, model/provider settings, task IDs and metric
estimands remain unchanged. The frozen dispatcher/error policy was not patched.

## Verified preflight and exact transaction

The comprehensive read-only audit matched Batches 1–11 (21,120 primary, 880
baseline, 342 canary records), all 1,832 valid Batch 12 records and its 1,833
physical attempts to archived evidence. The exact original failed request, prompt
hash and physical-attempt fingerprint matched. The sole invalid logical row was
Neo-Aristotelian virtue ethics × 29912, canonical. Exactly 198 scheduled tasks
remained (186 primary, six baseline, six final scheduled QC). The original $10
cap, persistent $1 stage cap, 2,000-primary-attempt ceiling, $1.184580525 confirmed
and $1.196829645 conservative spending, and zero outstanding reservations passed.
Original Batch 3 recovery evidence and all earlier records were unchanged.

The stopped incremental chain was restored and verified. A new consistent
pre-recovery SQLite backup was created and losslessly compressed, restored to an
isolated scratch file, exact-byte SHA-256 checked, integrity checked and compared
across schema and every table. Source/checkpoint/archive hashes are recorded in
`batch-0012-recovery/preflight.json` and `pre-recovery-checkpoint-provenance.json`.
The 4 GB temporary/preservation allowance plus 2 GB reserve fit available space.
No dependencies or history were removed. Backups remain on the working volume,
not independent volume-loss disaster recovery.

A disposable restored copy tested the unchanged `StageLedger`: retry eligible
claims are accepted as lifetime attempt 2; duplicate and already-valid claims
are refused; the original failed attempt remains intact; six fresh resume QC
requests are generated. No API calls were made by that compatibility test.

Under the exclusive experiment lock, `BEGIN IMMEDIATE` and a guarded primary-key
update changed **exactly one** evaluation from `invalid` to `retry`, with
`record IS NULL`. Any unexpected condition would roll back. Every other evaluation,
all physical attempts, settings, stage authorization and spending fingerprints
were unchanged before commit. Separate immutable intent and committed records
identify the transaction and investigator authorization hash. The original
physical attempt `9b4128fc0dcb469e817b209db3489378` retains its `invalid` classification,
HTTP 200/error-only internal 504 envelope, timestamps, full $0.002449824 charge and
fingerprint `a13e3481a060d4385bb41f5d60302af89884cf696bb8868faf6b2e938b385527`.
No refund, settlement rewrite, reset, replacement ledger or attempt-count reset
occurred.

## Authorized inference and second stop

The six fresh `b0012-resume0001-*` canaries all passed, with exactly matching raw
logs and stored conditional scores. Their finish timestamps precede all new
science-request starts. The reviewed canonical request succeeded on lifetime
attempt 2 using the identical original request. All earlier valid measurements
were skipped.

The invocation then encountered another HTTP 200/internal 504 error-only timeout:

| Field | New failure |
|---|---|
| Constitution / dilemma | Ubuntu / 29912 |
| Condition / replica | labels_swapped / 1 |
| Attempt ID | `429eb30c2dcd4a238d3fa886fdcb7b7e` |
| Internal error | `504`, `Upstream idle timeout exceeded` |
| Frozen classification | `Model/provider mismatch` |
| Model/provider/choices/logprobs/usage | absent |
| Full reservation retained | $0.002449824 |
| Attempt fingerprint | `21e4b4075c4032f070423ba4c4d6700a7fc72b98e073af2849248fa5847427ee` |

The missing identity in an error-only envelope does not establish that another
model was served. The frozen validator correctly stops under the current policy.
**No retry or reclassification of this new Ubuntu checkpoint was performed.**
It remains the only invalid logical evaluation. All requests settled and all
charges were checkpointed before offline preservation. All later dispatch is
blocked by the recovery-only scope and new second-stop record.

## Results, attempts and spending

| Quantity | This recovery invocation | Batch 12 total |
|---|---:|---:|
| Physical attempts | 198 | 2,031 |
| Valid responses | 197 | 2,029 |
| Failed physical attempts | 1 | 2 |
| Reviewed retry requests | 1 | 1 |
| Additional automatic retries | 0 | 0 |
| Confirmed charges | $0.009750348 | $0.099362357 |
| Conservative charges | $0.012200172 | $0.104262005 |
| Active inference seconds | 155.330 | 718.400 across both invocations |

The phase's 197 valid responses comprise 185 primary, six baseline and six fresh
resume canaries. The one reviewed retry is included in those 185 primary calls.
There are now 1,919 primary, 80 baseline and 30 canary records in Batch 12. Those
30 canaries comprise **24 scheduled + six resume**, not 30 scheduled. Seven
scheduled tasks remain: **one Ubuntu primary response and six final canaries**.
Primary physical attempts total 1,921, below 2,000. Original caps and lifetime
limits were verified unchanged, and outstanding reservations are zero.

All 2,029 valid Batch 12 responses match frozen requests/prompts, report Granite /
Cloudflare, and contain both genuine ASCII 0/1 next-token logs. Independent
raw/unconditional/conditional/semantic calculations differ by at most 2.23e-16.
Canary raw-logprob and stored probability differences are both zero. The four
partial matrices and their mean retain one blank primary/counterbalanced cell;
baselines are complete. Missing data was not imputed or replaced with sampled
answers. The 0.125 log-odds quantization limitation remains.

No full Batch 12 A/B/C matrices or 24×240 cumulative distance matrices were exported.
A 239-scenario complete-case substitution was deliberately not introduced. The
latest complete-batch cumulative result remains the unchanged 24×220 matrix and
A/B/C geometry (means normalized A 0.069121160, B 0.084713945, C 0.082583371). The
preliminary label/order/baseline and disjoint-subset diagnostics at 220 remain
historical, unchanged results; they are not new 240-scenario findings.

## Preservation and cumulative position

Post-recovery verification confirmed **all 24,174 previous valid evaluations** and
**all 24,183 historical physical attempts** unchanged. Other logical rows outside
missing authorized work were unchanged. The new Ubuntu failure is preserved
without a manual transition. A new incremental checkpoint,
`batch-0012-reviewed-recovery-stopped-ledger.sqlite.recovery.json`, was actually
restored with exact-byte, integrity, schema and all-table checks. It does not
replace the first stopped or pre-recovery checkpoints.

Original stopped exports are preserved under
`results/granite-exploratory/batch-0012-recovery/stopped-curated/`, with original
path/hash and copied path/hash maps. Earlier committed incident/progress reports
remain historical. The current `batch-0012/` view contains second-stop evidence;
new raw archives and preservation manifests distinguish the versions. A tested
nonfrozen backup locator can select a reviewed completed checkpoint without
replacing historical snapshots; no completed-checkpoint pointer was published
because the batch remains incomplete.

Cumulative state:

- 23,039 primary, 960 baseline, 372 canaries = **24,371 valid records**.
- Canaries: 354 scheduled + 18 resume (12 historical + 6 new).
- 24,381 physical attempts, ten failed attempts, six uncertain billing outcomes.
- **$1.194330873 confirmed / $1.209029817 conservative** against original $10 cap.
- The uncertain outcomes retain $0.014698944 total full-reservation charges.
- Zero outstanding requests/reservations; original failed charges remain intact.
- 239 scenarios fully observed; 11 fully completed batches, last complete analysis 220.

There are 111,257 scheduled evaluations remaining (105,217 primary, 4,384 baseline,
1,656 scheduled QC), across 56 unfinished batches including 12. Fifty-five stages
have not started. Aggregate active inference is 6,828.555 seconds (113.81 minutes),
3.56898 valid responses/s. This recovery's rate was 1.26827/s due largely to the
new timeout. Remaining projection: **8.66 active hours, $5.52 additional cost,
$6.73 total**, roughly ±20% plus review/setup and any restart QC/retries. Estimates
authorize no dispatch. A separately authorized continuation would need at least
13 calls for the remaining seven tasks plus six newly required resume canaries.

**The experiment is not ready for another multi-batch authorization while this
new checkpoint requires review.** Storage and budget remain adequate; the
operational blocker is the substantive frozen-policy stop. Only the investigator
can authorize another narrowly reviewed recovery. Do not execute 13,14 or later.

## Operational assessment

The request referred to two prior error-only HTTP 200 timeouts; this invocation
introduced a **third**. All three preserve full charges totaling **$0.007349472**
(actual external billing unknown). Their recorded failed-call lifetimes sum to
363.17 seconds;12 additional canaries after the Batch 3 and reviewed Batch 12 timeout
recoveries cost $0.000585736. Manual review, interruption and offline recovery work
are the larger operational cost; completed measurements have not been lost.

A future explicitly reviewed, separately versioned handler for narrowly validated
error-only upstream timeout envelopes is worth considering. It should retain
conservative billing and complete attempt history, respect existing bounded
lifetimes/caps, and continue rejecting actual identity mismatches or malformed
successful responses. **No such policy was activated in this recovery.**

Final tests: **79 passed**. Frozen inference environment, source hashes, settings
and scientific manifest remain unchanged. Credentials, SQLite databases and
compressed ledger objects remain outside Git; curated audit/results/docs are
committed and pushed. Same-volume backups do not provide independent disaster
recovery, and no external storage service was provisioned.
