# Batch 3 reviewed timeout recovery — complete, stopped after Batch 3

The investigator authorized recovery from committed state `ca04358`, exactly one
checkpoint transition, and completion of Batch 3 only. Batches 4 and 5 were not
executed or reactivated despite their earlier conditional authorization files.
Frozen run: `03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`. All scientific/source hashes, model/provider,
requests, probability definitions, $10 global cap and $1 persistent stage cap
remain unchanged.

## Recovery boundary and transaction

Before mutation, the original SQLite ledger passed integrity, manifest, input,
checkpoint and attempt-history checks. Batches 1–2 were unchanged. Batch 3 had
1,439 valid primary evaluations, 60 baselines and 18 canaries, with exactly 513
scheduled evaluations missing. Conservative spending was $0.283413186, with zero
reservations. The only invalid evaluation was Utilitarianism × 2599 × condition
1 (`labels_swapped`). Its original HTTP200 response contained exactly the reviewed
upstream timeout error with embedded code 504, no choices/model/provider or usage,
and its $0.002449824 charge remained intact.

A consistent, verified pre-recovery backup was made before the transition.
A disposable-copy test confirmed that the unchanged StageLedger accepts `retry`,
counts the original attempt, and refuses claims on valid checkpoints. Under the
exclusive experiment lock and a single `BEGIN IMMEDIATE` transaction, exactly
one SQL row changed: that logical evaluation's state `invalid` → `retry`.
The row's other columns were unchanged. Transaction ID:
`53955d739337409a800e3c88432e39a5`. Intent and committed records exist independently in
curated and operational storage. The original failed attempt retains its exact
request, response, recorded error, HTTP status, timestamps, charge and ID.

The unchanged runner issued six fresh resume canaries before any new scientific
request; all six matched exactly. It retried the target using its identical
request, succeeding on physical attempt 2 of the lifetime maximum 3, then completed
only pending tasks. All 519 new requests succeeded; no new error, null-log retry,
manual reinterpretation or provider drift occurred.

## Completed batch and preservation checks

Batch 3 has **1,920 valid primary evaluations, 80 baselines, 30 scheduled canaries
and six resume canaries**. There are 2,036 valid results and 2,037 physical
attempts, including the original failure, with 1,921 physical primary attempts
under the 2,000 cap. Missing scientific evaluations and outstanding reservations
are zero. Every valid response identifies Granite 4.0 H Micro and Cloudflare and
provides genuine literal ASCII 0/1 token logs. All 36 canaries have zero conditional,
raw-logprob and log-odds deviation.

The postcheck preserved all 5,583 previously valid evaluation rows, including
all 1,517 Batch 3 rows, and all 5,588 pre-existing physical attempts unchanged.
All Batch 1–2 operational/curated file fingerprints match. The original failed
attempt remains `invalid` in physical history; its logical evaluation is now
valid. No old cost was refunded or reset. The stopped response/attempt exports,
summary, missing list, report and backup manifest have `initial-stopped-` copies;
partial matrices and old incident reports remain historical, not current results.
Historical backups were not overwritten.

All four condition probability matrices, the four-condition mean matrix,
baseline, A/B/C normalized and summed distances, rankings, scenario contributions,
label/order diagnostics, subsampling and heatmaps are exported. Independent scalar
checks of every matrix entry have maximum error
4.44e-16; direct exp/logprob and swapped-label
checks have maximum error 2.22e-16.
There is no imputation. Minimum binary-token mass in scientific responses is
0.998343; no valid sampled output violated the required format. All scientific
log odds remain on the observed 0.125 grid within the documented tolerance.

## Scientific results, preliminary scope

The pooled first 60-scenario analysis is recomputed from individual condition
probability vectors, not batch-distance averages. A compares four-condition mean
vectors; B averages condition-specific distances; C uses canonical prompts.
Summed distances divide by N = 60 for normalized versions. A and B remain distinct.

| Scenarios | Mean A | Mean B | Mean C | A rank correlation with previous prefix |
|---|---:|---:|---:|---:|
| 20 | 0.069554 | 0.089354 | 0.103897 | — |
| 40 | 0.075908 | 0.093832 | 0.103397 | 0.850548 |
| 60 | 0.069559 | 0.086447 | 0.093719 | 0.957333 |

From 40 to 60, B/C distance-ranking correlations are 0.966091/0.968918;
19/24 A nearest neighbors, 18/24 B and 19/24 C remain unchanged (ID tie-breaks).
These are partial-library exploratory observations, not final rankings.
For 30-of-60 subsampling, mean A-ranking correlation is 0.887362 with 5th–95th
percentile 0.845454–0.921033 over 100 fixed-seed draws. Batch 3's mean absolute
label effect is 0.236497, order effect 0.114622 and four-condition range 0.375966.
These sizable prompt effects and log-odds quantization remain limitations even
with counterbalancing. Interpret everything as Granite-conditioned behavioral
geometry, not established philosophical distance or perfect constitutional fidelity.

## Costs, performance and boundary

| Scope | Confirmed charges | Conservative spending |
|---|---:|---:|
| Batch 1 | $0.099496116 | $0.099496116 |
| Batch 2 | $0.099736308 | $0.107085780 |
| Batch 3 complete | $0.099814508 | $0.102264332 |
| Experiment cumulative | $0.299046932 | $0.308846228 |

This recovery added **$0.025433042**. Four historical unknown billing outcomes
remain charged in full, totaling $0.009799296 above confirmed charges. Exact final
billing is not yet known. No charges occurred through other inference providers.

Recovery active dispatch took **190.676s**
(3.18min), at
2.722 new valid requests/s.
Total Batch 3 active dispatch across both invocations is
**750.181s** (12.50min), at
2.714 valid requests/s. Approval/review downtime
is excluded. Experiment-wide active dispatch is
1754.837s
(29.25min), averaging
3.477 valid requests/s.

Cumulative completion is 60 scenarios: 5,760 primary, 240 baseline, 102 canary results
(90 scheduled + 12 resume), 6,102 valid and 6,107 physical attempts. Five failed attempts
remain in history. Remaining: 1,276 scenarios across 64 batches, 122,496 primary,
5,104 baseline and 1,920 scheduled QC measurements. Estimated remaining cost is
$6.56, or
$6.86 total. Expected remaining active time is
10.35h. Allow roughly
±20% variation plus setup, approvals, throttling and extra resume checks.
The $10 cap has $9.691153772 remaining.

The experiment is technically ready for the next stage, but this task does not
reactivate the old sequence. Explicit authorization is required before Batch 4 or5.
The proposed future HTTP200 error-envelope policy is separately documented in
`granite-upstream-error-policy-proposal.md`; it is not implemented or activated.
Current scientific sources and dispatcher hashes remain frozen.
