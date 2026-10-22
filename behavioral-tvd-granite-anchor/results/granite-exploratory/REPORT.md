# Approved exploratory experiment: batch 1 complete, execution stopped

The investigator-approved experiment characterizes **Granite-conditioned
behavioral geometry under the 24 constitutional prompts**, not philosophical
distances or perfect implementation of ethical principles. The protocol and
scenario-selection policy are finalized for this exploratory objective.

Frozen run:
`03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.
Only batch 1 was dispatched. There is no authorization file or dispatch-stage
record for a later batch.

## Frozen design and dry run

The included 1,336 scenarios are exact original objects, with situations,
`to_do`/`not_to_do` actions, topic groups and topic IDs preserved. All 24 flagged
scenarios (15 ambiguous, nine other review cases) are excluded from primary and
baseline grids, with their original text separately preserved. Approval is an
**investigator-approved automated-screening policy**, not individual human
certification. The previous audit and pilot evidence were not edited.

There are 128,256 primary tasks, 5,344 baseline tasks and 2,010 scheduled canaries
across 67 batches. Fresh resume canaries, if needed, are additional QC tasks under
the same caps. The offline dry run made zero API requests, verified 135,610 unique
planned task identities and their request hashes, and matched the renderer
against all 4,000 prior pilot main/baseline requests. The selected IDs, exact
inputs, settings, source hashes and task-hash plan are versioned.

Settings remain exactly tested: `ibm-granite/granite-4.0-h-micro`, OpenRouter
`cloudflare` only, fallbacks disabled, required parameters, temperature 1, top_p 1,
max_tokens 1, logprobs true and top_logprobs 20. No tokenizer, model, provider,
constitution or scenario wording was changed. The 0.125 log-odds quantization
limitation remains documented and was observed again in this batch.

## Batch 1 execution

Twenty scenarios were selected by the frozen global shuffle, seed 20261021,
covering 12 topic groups. Each has all 24 constitutions and four conditions;
baselines use the same four tested no-constitution conditions. Request ordering
is interleaved within five-scenario chunks; concurrency never exceeds three.

| Item | Result |
|---|---:|
| Valid primary evaluations | 1,920 |
| Valid baseline evaluations | 80 |
| Valid canaries | 30 |
| Total valid records | 2,030 |
| Physical primary attempts, including retry | 1,921 / 2,000 cap |
| All physical attempts | 2,031 |
| Failed attempts | 1, recovered |
| Unresolved batch evaluations | 0 |
| HTTP statuses | 2,031 × HTTP 200 |
| Actual/accounted spending | **$0.099496116** |
| Dispatch-stage cap | $1 |
| Experiment-wide cap | $10 |
| Outstanding reservations / unknown billing | 0 / 0 |
| Billed input / completion tokens | 5,839,332 / 2,031 |

The one failure was **Taoism × 30846, reversed action-line order**, returning
`logprobs:null` at HTTP 200. It cost $0.000047576 and was preserved as a failed
attempt. Its first additional attempt succeeded after bounded backoff. No task
required a third attempt. The experiment did not silently discard the failed call,
substitute a sampled answer, or recompute any completed valid evaluation.

All 30 canaries returned exactly matching reference conditional probabilities,
raw label logs and log odds: maximum differences were **zero**. All 2,030 valid
responses reported the expected Granite model and `Cloudflare`. Both answer-token
logs were finite in every valid evaluation. Minimum two-answer unconditional mass
was 0.997286, and there were no sampled-format violations. Provider-reported
identity is not independent attestation of internal weights/hardware.

Elapsed dispatch time was **505.94 seconds (8 minutes 26 seconds)**, including
canaries, retry and checkpoint exports: **4.012 valid evaluations/second**, or
3.795 primary evaluations/second. Mean recorded attempt latency was 0.701 seconds.

## Batch-scope analysis

The following are results for **these 20 scenarios only**, not the final
1,336-scenario experiment. For semantic conditional probabilities p[c,s,k] and
q[c,s]=mean_k p[c,s,k]:

| Metric | Definition | Mean normalized distance over 276 constitution pairs |
|---|---|---:|
| A, primary | mean_s abs(q[c,s]−q[d,s]) | 0.069554 |
| B, secondary | mean_k mean_s abs(p[c,s,k]−p[d,s,k]) | 0.089354 |
| C, robustness | canonical mean_s abs(p[c,s,0]−p[d,s,0]) | 0.103897 |

A and B were computed separately, with B >= A checked; their maximum normalized
gap was 0.056823. All three have normalized and summed-L1 matrices, with summed
versions equal to 20 times their normalized values. All matrices are symmetric,
nonnegative, and have zero diagonals. Independent recomputation differed by at
most 4.44×10⁻¹⁶. All 2,030 actual request/message hashes matched the frozen plan;
there were no duplicated identities or missing probabilities.
All **63 automated tests pass**, including concurrent reservation/cap checks,
idempotent and partial resume, bounded null-log retries, drift/mismatch stops,
and duplicate prevention. All 317 pre-existing tracked files remain unchanged;
the new-file credential scan found no secrets.

Canonical versus primary pair-distance Spearman correlation was 0.8083. Mean
absolute label-mapping effect was 0.3760; action-line order effect 0.1583; mean
four-condition probability range 0.5637. These nuisance sensitivities remain
substantial and are part of the measured Granite behavior, not evidence about
intrinsic philosophical geometry.

Across constitutions, mean absolute counterbalanced shift from the separate
ordinary-judgment baseline averaged **0.1190**, ranging 0.0959–0.1514. Such shifts
include constitution-text presence, framing and length effects; they do not
isolate faithful normative application. Four condition-specific probability
matrices, averaged probabilities, baseline vectors/shifts, A/B/C distance
matrices, rankings, per-scenario contributions and heatmaps are saved in
`batch-0001/`.

Exploratory within-batch subsampling (100 draws per size, seed 20261022) gave mean
primary-distance Spearman correlations of 0.6525 using five scenarios and 0.8326
using ten, relative to the 20-scenario batch. These are descriptive sensitivity
checks, not population guarantees or a substitute for the full experiment.
Complete-library exports refuse to run until the scientific grid and canary
schedule are complete and billing/in-flight outcomes are reconciled. The refusal
was checked offline without inference.

## Remaining work and projections

| Remaining component | Evaluations |
|---|---:|
| Primary | 126,336 |
| Baseline | 5,264 |
| Scheduled canaries | 1,980 |
| Total scheduled remaining | 133,580 |
| Remaining batches | 66 |

At this batch's token usage and throughput, projected remaining inference cost is
**$6.55**, for approximately **$6.65 total**, including the observed retry-rate
allowance and scheduled baseline/canary work. Projected remaining active inference
time is **9.25 hours**. Allow roughly ±20% variation, plus task startup, provider
throttling/price changes, extra resume QC, and manual approval delays. These are
projections, not guarantees or authorization for more dispatch.

The single authoritative experiment ledger is under
`/workspace/work/granite-exploratory/<run_id>/ledger.sqlite`. Its stable run/task
keys, immutable manifest, persistent $10 cap and per-stage reservations remain
available for resume. A consistent SQLite backup and checksum are stored under
`/workspace/backups/granite-exploratory/<run_id>/`; raw responses, all physical
attempts, endpoint observations, authorization and execution snapshots are
curated here. Credentials and ledgers are excluded from Git.

**Execution is stopped. Batch 2 requires explicit investigator authorization.**
Future tasks must use this same manifest, task identities and ledger, create only
the specifically authorized stage approval, and retain all budget/QC safeguards.
No additional methodological approval is presumed necessary for the explicitly
accepted exploratory interpretation; no later batch is silently authorized.

Protocol: [`docs/granite-exploratory.md`](../../docs/granite-exploratory.md).
