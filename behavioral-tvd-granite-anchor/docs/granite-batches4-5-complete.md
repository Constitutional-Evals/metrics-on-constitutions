# Granite Batches 4–5 reactivation and completion

**Both batches completed. Execution is stopped after Batch 5; Batch 6 and later have no authorization.**

Frozen run: `03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`. Base commit: `886d53b`.

The investigator explicitly reactivated exactly Batches 4 and 5 sequentially. The new
`configs/granite-exploratory-reactivations/batches-0004-0005.json` links the original
conditional authorization files by SHA256, preserving their bytes and all earlier
stop and recovery evidence. The latest instruction superseded the prior block for
these two stages only. The frozen scientific configuration and dispatcher were not
changed; the proposed upstream-error policy remains inactive.

The original authoritative SQLite ledger, manifest, frozen input/source hashes,
all prior checkpoints and attempt histories were verified before dispatch. Batches
1–3 contained 5,760 primary, 240 baseline and 102 canary valid records, with
$0.308846228 conservatively charged under the existing $10 cap and no reservations.
Batch 3’s original failed attempt, $0.002449824 charge and recovery audit were
verified unchanged. A consistent pre-Batch-4 backup was made. All 63 tests passed.

The runtime status tool returned unknown readiness fields and no retained diagnostic
history. An authenticated, read-only OpenRouter /key request succeeded (HTTP200,
zero inference). The frozen dispatcher then used the existing proxy, authenticated
API and normal endpoint/canary checks. Every actual valid inference response was
verified independently. No credential value or /key response body was saved.

## Completion and accounting

| Batch | Primary | Baseline | Scheduled QC | Attempts | Failed attempts | Confirmed | Conservative | Active seconds | Valid/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1,920 | 80 | 30 | 2,031 | 1 | $0.099542798 | $0.099542798 | 551.060 | 3.684 |
| 5 | 1,920 | 80 | 30 | 2,030 | 0 | $0.099518240 | $0.099518240 | 552.768 | 3.672 |

Batch 4’s Kindness × 32872 × both_reversed response had `logprobs:null`. The
unchanged dispatcher performed one allowed retry, which succeeded; the failed
attempt’s known cost was $0.000051758. No checkpoint was reclassified manually.
Batch 5 had no failed attempts or retries. There were no new ambiguous billing
outcomes, transport interruptions, provider mismatches or exhausted retries.
All 60 new canaries matched both raw logs and conditional probabilities exactly.
Every valid response reports the requested Granite model and Cloudflare and has
both genuine ASCII 0/1 next-token logs. Missing probabilities were never imputed.

After Batch 4, independent probability and A/B/C checks, spending reconciliation,
prior-record preservation and ledger/raw-evidence backups all passed before Batch
5 became eligible. Its before-stage backup equals the verified Batch 4 backup.
Equivalent checks passed after Batch 5. The pre/post audits fingerprint all prior
valid rows, complete paid-attempt histories, stage authorizations and batch files.
All frozen-source hashes passed; all prior completed evaluations remain unchanged.

Both stages retain the $1 persistent cap, 2,000 physical primary-attempt limit
(Batch 4: 1,921; Batch 5: 1,920), concurrency 3 and lifetime 3-attempt limit. No new
resume invocation was needed, hence no extra restart canaries in these two batches.
Cumulative canaries comprise 150 scheduled and 12 earlier resume checks.

The task added **$0.199061038** and used **1103.828s** (18.40min) of active dispatch.
Cumulative confirmed charges: **$0.498107970**; conservative spending: **$0.507907266**.
Four historical unknown billing outcomes retain $0.009799296 in full conservative
charges. They were not refunded or reset; exact final billing remains unknown.
There are 10,168 physical attempts, including 6 failed attempts, and 10,162 valid results.
No in-flight requests, missing evaluations in completed batches, or held budget
reservations remain. The original experiment cap stays $10.

## Preliminary cumulative science

The 24×100 semantic probability matrix and four condition-specific matrices,
baseline vector, and A/B/C 24×24 normalized/summed distances were reconstructed
from individual response records. No batch-matrix averaging was used. A computes
distance between four-condition mean vectors; B averages condition-specific
distances; C uses canonical prompts. Normalization divides sums by actual N=100.
Independent scalar checks of all cumulative distances have maximum error 5.33e-15.
Symmetry, zero diagonal, nonnegativity, probability range, completeness and A≤B
checks passed. Batch-specific matrices remain separately labeled.

| Prefix N | Mean normalized A | A rank correlation with previous prefix | Unchanged A nearest neighbors | Mean absolute A-distance change |
|---|---:|---:|---:|---:|
| 20 | 0.069554 | — | — | — |
| 40 | 0.075908 | 0.850548 | 6/24 | 0.009383 |
| 60 | 0.069559 | 0.957333 | 19/24 | 0.006853 |
| 80 | 0.070735 | 0.966590 | 17/24 | 0.003150 |
| 100 | 0.069849 | 0.987242 | 21/24 | 0.001859 |

| Metric over 100 scenarios | Mean normalized distance | Mean summed L1 |
|---|---:|---:|
| A_primary | 0.069849 | 6.984856 |
| B_secondary | 0.086298 | 8.629798 |
| C_canonical | 0.087646 | 8.764588 |

From 80 to 100, maximum pairwise A-distance change is 0.007148 (Judaism–Marxism,
0.073535→0.066388). Three nearest neighbors change: Christianity shifts from
Hinduism to Buddhism; Hinduism from Christianity to Judaism; Kindness from Buddhism
to Judaism. ID tie-breaks are retained. All per-pair changes and per-constitution
neighbor histories are exported; these observations do not establish final rankings.

For 50-of-100 scenario subsets, mean A-ranking Spearman is 0.932721 with descriptive
5th–95th percentile 0.902540–0.954041; for 25-of-100 it is 0.829438,
0.747933–0.884138. Each uses 100 fixed-seed draws without replacement, seed 20261022.
These describe sensitivity within the observed set, not population confidence bounds.

Mean absolute label-mapping effect is **0.306881**; action-order effect **0.172687**; mean four-condition range **0.500467**.
Mean absolute constitution-to-baseline shift is **0.108012**, signed shift **0.021798**.
Across constitutions, mean absolute baseline shifts range from 0.088858 to 0.141489.
Substantial prompt sensitivity persists despite counterbalancing. The observed
0.125 log-odds grid and imperfect constitutional fidelity remain limitations.
All new scientific log odds lie on that grid within the existing 1e-5 tolerance.
These are preliminary Granite-conditioned prompt-induced behavioral distances,
not validated philosophical distances or the final 1,336-scenario experiment.

## Remaining work and recommendation

Remaining: **118,656 primary**, **4,944 baseline**, **1,860 scheduled QC** evaluations over **62 batches** and 1,236 scenarios.
Cumulative active time: 2858.665s (47.64min), at 3.555 valid evaluations/s.
Projected remaining cost: **$6.27**, or **$6.78 total**, with **9.80 active hours remaining**.
Allow roughly ±20% usage/throughput variation, plus setup/review delays, throttling
and additional restart canaries. The $10 cap remains binding; no forecast authorizes
dispatch. Unspent global budget is $9.492092734.

A modest next group of three batches (6–8) would be reasonable only with explicit
investigator authorization, the same per-stage gates/caps and stop-on-review rules.
Expected observed-usage cost is approximately $0.30 and 27–30 active minutes. This
recommendation does not authorize that group; unexpected HTTP200 error envelopes
still require review under the unchanged dispatcher.

Consistent ledger backups and complete raw/curated evidence archives are stored
separately outside Git, with hashes in each batch preservation manifest. All
historical backups and stopped/recovered evidence are retained. The authoritative
ledger and credentials are excluded from Git; curated raw response/attempt evidence
and provenance are included.
