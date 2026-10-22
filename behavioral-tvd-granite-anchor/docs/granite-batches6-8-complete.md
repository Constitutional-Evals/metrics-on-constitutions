# Granite Batches 6–8: completed, stopped after Batch 8

**Batches 6, 7 and 8 completed sequentially. Batch 9 and later have not been authorized or executed.**

Frozen run: `03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`. Reviewed base commit: `b1daccf`.

The original authoritative SQLite ledger, frozen manifest, input/source hashes,
task identities and all preceding checkpoint/attempt records passed preflight.
Batches 1–5 contained 9,600 primary, 400 baseline and 162 canary valid records,
with $0.507907266 conservatively charged under the unchanged $10 cap. There were
no outstanding reservations or unresolved measurements in completed batches.
All prior errors, charges, backups and Batch 3 recovery records are retained.
The network policy and credential binding reported enforced/ready before use.

Explicit immutable authorizations cover only [6,7,8], linked by SHA256 in
`configs/granite-exploratory-authorizations/groups/batches-0006-0008.json`.
Each uses the original $1 persistent stage cap, 2,000 physical primary-attempt
ceiling including retries, concurrency three and three lifetime attempts per
logical evaluation. The frozen dispatcher, provider pinning, prompts, probability
extraction, retry rules and canary thresholds were not modified. Only offline
audit/analysis tooling was extended. The upstream-error policy proposal is inactive.

## Per-batch execution and independent checks

| Batch | Primary | Baseline | Canaries | Physical attempts | Failed | Confirmed | Conservative | Active seconds | Valid/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | 1,920 | 80 | 30 | 2,032 | 2 | $0.099602546 | $0.099602546 | 532.834 | 3.810 |
| 7 | 1,920 | 80 | 30 | 2,030 | 0 | $0.099518240 | $0.099518240 | 558.273 | 3.636 |
| 8 | 1,920 | 80 | 30 | 2,030 | 0 | $0.099453640 | $0.099453640 | 521.680 | 3.891 |

Batch 6 had two HTTP200 `logprobs:null` responses: Hinduism × 21167 × labels_swapped
($0.000045570) and Judaism × 32963 × labels_swapped ($0.000047236). Each identical
request succeeded on its first permitted retry (two lifetime attempts). Both
failed physical records, responses and known costs are preserved. Batches 7 and
8 had no failed attempts or retries. No manual checkpoint reclassification, new
ambiguous billing outcome, exhausted retry or provider drift occurred.

Each predecessor passed probability/matrix checks, spending reconciliation,
old-record preservation and ledger/raw-evidence backup verification before its
successor began. All 90 new scheduled canaries exactly match conditional
probabilities and raw log probabilities; no new resume invocation was needed.
Every valid response identifies the frozen Granite model and Cloudflare and
contains genuine literal ASCII 0/1 token logs. All actual requests and prompt hashes
match the frozen task plan. The original failed Batch 3 attempt and its full
$0.002449824 conservative charge are unchanged. No valid task was recomputed.

All four 24×20 semantic probability matrices, their four-condition mean, baseline
results and separate A/B/C normalized/summed distances are exported per batch.
Independent checks recompute probabilities from the raw token logs and every
matrix entry using scalar sums. Probability ranges, completeness, symmetry, zero
diagonal, nonnegativity and A≤B checks passed. There is no missing-value imputation.
Minimum scientific binary-token mass is 0.997221; all valid sampled answers conform
to the required format. All new scientific log odds remain on the 0.125 grid within
the existing 1e-5 tolerance.

## Cumulative first-160 science

The pooled 24×160 counterbalanced and four condition-specific probability matrices,
baseline vector and 24×24 A/B/C distances were reconstructed from individual
records. No batch-distance averaging was used. A compares four-condition mean
vectors; B averages the four condition-specific distances; C uses canonical
prompts. Normalized distances equal summed L1 divided by N=160.
Maximum independent scalar error is 5.33e-15.

| Metric | Mean normalized distance | Mean summed L1 |
|---|---:|---:|
| A_primary | 0.069753 | 11.160495 |
| B_secondary | 0.086156 | 13.784889 |
| C_canonical | 0.085546 | 13.687419 |

| Prefix N | Mean A | Rank correlation with previous prefix | Unchanged A nearest neighbors | Mean absolute pair-distance change |
|---|---:|---:|---:|---:|
| 20 | 0.069554 | — | — | — |
| 40 | 0.075908 | 0.850548 | 6/24 | 0.009383 |
| 60 | 0.069559 | 0.957333 | 19/24 | 0.006853 |
| 80 | 0.070735 | 0.966590 | 17/24 | 0.003150 |
| 100 | 0.069849 | 0.987242 | 21/24 | 0.001859 |
| 120 | 0.069450 | 0.988613 | 22/24 | 0.001805 |
| 140 | 0.069262 | 0.987911 | 24/24 | 0.001684 |
| 160 | 0.069753 | 0.990311 | 22/24 | 0.001506 |

From 140 to 160, maximum absolute pair-distance change is 0.005964. Full per-pair and per-constitution neighbor changes are exported.
Nested prefix comparisons are statistically dependent: the first 140 scenarios
are present in both the 140- and 160-scenario matrices. High apparent stability can
partly result from shared data; it does not by itself establish population convergence.

## Disjoint robustness check

The first 80 and next 80 scenarios are consecutive, non-overlapping halves of the
same frozen schedule. The exact IDs, independent A matrices, per-pair absolute
differences and nearest-neighbor assignments are exported. There was no reselection
or change to the scientific protocol.

- Scenario overlap: **0**.
- Primary A-distance Spearman correlation: **0.791924**.
- Mean/median/max absolute normalized-distance differences: **0.007503 / 0.006209 / 0.026922**.
- Nearest-neighbor agreement: **10/24 (41.67%)**.
- Mean normalized A distance: first 80 **0.070735**, next 80 **0.068771**.
- Independent scalar verification error: 2.78e-17.

This disjoint comparison is meaningfully less stable than the nested 140→160
comparison (rho 0.792 versus 0.990; 10/24 versus 22/24 nearest neighbors unchanged).
It reveals remaining scenario sensitivity despite similar average distances.
The two sets still share the same model, constitutions and collection procedure;
pair distances also share constitutions. Reported correlations are descriptive,
not independent-edge hypothesis tests, philosophical validation or confidence
bounds for the full scenario population.

For 80-of-160 fixed-seed subsets, mean A-ranking Spearman is 0.947199 with descriptive
5th–95th percentile 0.928826–0.962066; for 40-of-160 it is 0.862610,
0.802000–0.905884. Each uses 100 draws without replacement, seed 20261022.

Mean absolute label effect is **0.292818**, action-order effect **0.175523**, and four-condition range **0.488103**.
Mean absolute constitution-to-baseline shift is **0.105851**, signed shift **0.032316**.
These substantial prompt effects, approximate 0.125 log-odds quantization and
imperfect constitutional fidelity remain explicit limitations. Results describe
preliminary Granite-conditioned behavior over 160 scenarios, not final 1,336-scenario
or established philosophical distances.

## Spending, performance and remaining work

This group added **$0.298574426** in both confirmed and conservative charges and used **1612.787s** (26.88min).
Cumulative confirmed spending is **$0.796682396** and conservative spending **$0.806481692** against the original $10 cap.
Four historical unknown billing outcomes retain their full $0.009799296 charges.
There are no new unknown costs, refunds, replacements or budget resets. No
requests or reservations remain in flight. All earlier errors and recovery
evidence remain unchanged.

Cumulative completion: **160 scenarios, 15,360 primary, 640 baselines, 252 canaries** (240 scheduled + 12 historical resume). There are 16,260 physical attempts and 8 historical failed attempts.
Cumulative active time: **4471.452s** (74.52min), averaging **3.635 valid/s**.
Remaining: **112,896 primary**, **4,704 baselines**, **1,770 scheduled canaries**, across **59 batches** and 1,176 scenarios.
Projected remaining inference cost: **$5.92**, or **$6.73 total**. Estimated remaining active dispatch is **9.12h**.
Allow roughly ±20% usage/throughput variation plus setup, review delays, throttling
and added restart QC. These are inference projections, not guarantees or later
batch authorization. The original spending cap remains binding.

## Storage and next-group recommendation

The volume has 19.12GB free. The latest full ledger snapshot is 650.3 MB, growing about 77.5 MB per batch.
Retaining the current full before/after snapshots projects **8.44GB** for the next 5 batches and **20.76GB** for 10, before extra raw/evidence/Git growth.
Ten batches would exceed current free storage on snapshots alone. Five are
reasonable with explicit new authorization, per-batch verification/backup gates,
the same inference caps and stop rules, and storage-headroom checks. At observed
usage, five batches cost about $0.50 and take 44–47 active minutes. Do not increase
to ten under the current storage arrangement. Plan external archival, additional
capacity or an explicitly reviewed backup-storage strategy before later groups;
no historical backup was deleted, overwritten or deduplicated by this task.
No new storage subscription or external service was provisioned.

The authoritative ledger and raw evidence have consistent, independently verified
backups outside Git. Curated raw API/attempt evidence, verification, analysis and
documentation are committed; credentials and the authoritative SQLite are excluded.
All 66 automated tests pass, including new analytical, missing-value and duplicate-ID
tests for the disjoint comparison. **No Batch 9 or later authorization was created.**
