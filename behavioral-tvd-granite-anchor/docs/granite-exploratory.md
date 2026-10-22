# Approved exploratory Granite experiment

The investigator approved an exploratory characterization of **behavior induced
by Granite under the 24 constitutional prompts**. These distances are not
established philosophical distances, nor a claim that Granite faithfully
implements each ethical system. The final pilot's fidelity failures and numerical
limitations remain part of the scientific record.

The immutable manifest is `configs/granite-exploratory-approved.json`, run ID
`03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e`.
Only `batch-0001` has execution authorization. Preparing the full task grid does
not authorize later batches. The historical pilot, previous audit decisions, and
older blocked proposals remain unchanged.

## Scenario approval and frozen inputs

The investigator accepted the existing automated screen as a selection policy:
include the 1,336 provisionally valid scenarios and exclude all 24 flagged ones
(15 ambiguous, nine requiring other review) from primary and baseline grids.
This is **investigator approval of an automated-screening policy**, not individual
human certification of 1,336 semantic judgments. Ambiguities can remain among
included cases; the selection process can affect measured geometry.

`data/granite-exploratory/` snapshots the included scenario file byte-for-byte,
the complete original 1,360-scenario library, all excluded original objects,
24 constitution files, and the approval/ID lists. Original situation, both action
descriptions, topic group, and topic ID are unchanged. Each included object was
checked equal to its original counterpart. All 1,336 IDs are unique; none of the
24 excluded IDs enters the primary or baseline grid. Established canary requests
are separate QC controls, not additions to those grids.

The manifest records source/snapshot hashes, the exact model settings, all four
prompt examples/rendering rules, constitution order and contents, scenario order
and contents, canary reference payloads/distributions, deterministic batch IDs,
and execution rules. The compressed offline task plan records every planned
identity and exact request/message hash. Rendering was exhaustively checked
against all 4,000 prior pilot main/baseline requests: exact payload equality.

Historical source provenance remains in `data/constitutions/SOURCE.md` and
`data/scenarios-v2.source.json`; their inputs and prior artifacts are preserved.
`values_aggregated` and `negative_consequence` annotations never enter the prompts.

## Model, probabilities, and scientific estimands

Use only `ibm-granite/granite-4.0-h-micro`, OpenRouter `cloudflare`:
temperature 1, top_p 1, max_tokens 1, logprobs true, top_logprobs 20,
`provider.only=["cloudflare"]`, `allow_fallbacks=false`, `require_parameters=true`.
The tested maximum prices remain $0.017/M input and $0.112/M output tokens.
No seed, logit bias, response-format constraint, tokenizer download, or other
inference parameter is added. Metadata calls check exact endpoint availability,
supported parameters, pricing ceilings, and context; they are not inference.
Changes to frozen inference code/inputs fail hash checks and require a separate
experimental version rather than silently changing a live run.

Use genuine next-token logs `l0,l1` for literal single tokens `0` and `1`.
Unconditional probabilities are `exp(l0), exp(l1)`, while the conditional
forced-choice probability of token 1 is `sigmoid(l1-l0)`. Semantic `p(to_do)`
uses that probability for canonical labels and `sigmoid(l0-l1)` when swapped.
Both raw logs, unconditional probabilities, binary mass, conditional probability,
sampled output, and format flags are retained. A non-label sampled output does
not replace or invalidate a genuine measured distribution by itself.

The four conditions independently manipulate label mapping and the order of the
two action-label lines. The original situation remains verbatim, including any
ordering embedded in its prose. These operational manipulations do not isolate
digit identity from every presentation detail. Constitutions share identical
scenario messages and instruction templates within a condition, varying only
constitution contents. Baselines use the exact tested no-constitution wording.

For constitution c, scenario s, condition k, let p[c,s,k] denote the semantic
conditional probability. Let q[c,s] be its mean across the four conditions and
N the number of included scenarios:

* **A, primary:** `(1/N) sum_s |q[c,s]-q[d,s]|`.
* **B, secondary:** `(1/4) sum_k [(1/N) sum_s |p[c,s,k]-p[d,s,k]|]`.
* **C, robustness:** canonical `(1/N) sum_s |p[c,s,0]-p[d,s,0]|`.

All three also have summed-L1 versions, multiplying by N. A is distance between
average vectors; B is average distance, and B >= A by Jensen's inequality.
They must never be conflated. A measures average behavior under a uniform
distribution over these four encodings; averaging can conceal encoding-specific
inconsistency, so condition vectors and ranges remain available.

The four-condition no-constitution baseline is separate from the 24×24 matrix.
Report constitution-to-baseline signed and absolute shifts. These shifts include
effects of instruction presence, prompt length, and framing; they do not by
themselves isolate faithful application of ethical content.

The pilot showed a 0.125 log-odds grid despite long printed decimals. Retain this
finite-precision limitation; exact repeatability is not arbitrary numerical
precision or semantic validity. Provider-reported model identity cannot
independently attest backend weight versions or hardware.

## Counts, batching, and authorization

There are 128,256 primary tasks (24×1,336×4), 5,344 baselines, and 2,010 scheduled
canaries: **135,610 planned valid records**. Six additional fresh canaries precede
resumption of any incomplete stage; these adaptive QC records have separate,
persisted identities and remain within all monetary caps.

Scenarios are shuffled once with seed 20261021 and divided into 67 batches:
66 of 20 scenarios, then 16. Within each five-scenario chunk, all constitutions,
conditions, and baselines are interleaved using the frozen seed rule. Each full
batch has 1,920 primary tasks, 80 baselines, and 30 canaries. Six established
canaries run before the first chunk, between chunks, and at the end. Concurrency
is at most three, including retries and QC.

The first stage has a **2,000 physical primary-attempt ceiling including retries**,
not just a logical-evaluation limit. Its 1,920 logical primary tasks leave room
for up to 80 primary retry attempts. Baselines and canaries are separately counted
and share the stage's monetary cap. No command loops automatically into the next
batch; a missing matching authorization file fails before any inference.

The total new-experiment budget is $10, separate from the previous $0.75 pilot.
This reuses the established transactional ledger implementation with an added
atomic stage-reservation layer. There is **one new experiment-wide ledger**, not
a fresh budget or independent ledger for each stage. Batch 1's persistent cap is
$1. Both budgets default to zero in dispatch code; explicit authorization is
required. Stage and experiment limits include outstanding reservations across
concurrent requests. Each request conservatively reserves 110% of entire-context
input cost plus one output token, ignoring cache discounts. Unknown billing
outcomes retain conservative charges. Restarting cannot reset a stage cap.

The approved root is
`/workspace/work/granite-exploratory/03473f2875b447f77273de536b3b8af4c9d94293380a5cabe8b2cd0a1bf5fd9e/`.
The authoritative `ledger.sqlite` uses transactional claims, unique run/task
keys, WAL and FULL synchronous mode. Valid tasks are checked and skipped on
resume. Previously completed pilot responses are not reused as new experiment
measurements. An uncertain in-flight request keeps its reservation and blocks
automatic resume until reconciled. A missing authoritative ledger is not
reconstructed from partial exports to reissue paid calls.

## Errors, QC, and checkpoints

An occasional `logprobs:null` may receive **two additional attempts maximum**,
each individually recorded, billed/reserved, and delayed by bounded 2/4-second
backoff. The same lifetime three-attempt ceiling applies across restarts and
transient HTTP/network failures; it is not three attempts per invocation.
After exhaustion the evaluation remains explicitly missing and the batch stops.
Non-null missing label tokens, malformed distributions, wrong identity, and
significant canary drift stop dispatch immediately. Already-issued calls settle;
there is no automatic provider fallback, probability imputation, or sampled-answer
substitution. Failed calls remain in the attempt history even after a successful
retry.

Canary tolerances are absolute 0.001 for conditional probability and 0.01 for log
odds/raw label logs. Expected values and exact requests come from the established
pilot canaries. Resuming incomplete work first adds a fresh, separately identified
QC round; completed scientific evaluations are not recomputed. Completed stages
resume without new inference.

Every response is durably settled before being counted complete. Atomic exports
at chunk boundaries and finalization are rebuildable from SQLite. Each batch
reports counts, failures, costs, reservations, rate, remaining tasks and projected
time/cost. Raw request/response and failed-attempt evidence are compressed for
version control; ledgers are excluded from Git and backed up separately.

## Execution and offline analysis

These preparation commands make **zero API requests**:

```bash
PYTHONPATH=src .venv/bin/python scripts/granite_exploratory.py dry-run
.venv/bin/python -m unittest discover -s tests
```

Only the first batch is authorized in this task:

```bash
PYTHONPATH=src .venv/bin/python scripts/granite_exploratory.py execute \
  --batch 1 --experiment-budget-usd 10 --stage-budget-usd 1
```

After it settles, analysis and preservation do not call inference:

```bash
PYTHONPATH=src .venv/bin/python scripts/analyze_granite_exploratory.py --batch 1
PYTHONPATH=src .venv/bin/python scripts/preserve_granite_exploratory.py --batch 1
PYTHONPATH=src .venv/bin/python scripts/verify_granite_exploratory_batch.py --batch 1
```

Each batch's matrices use only its completed scenario set and are labeled batch
scope, not the full 1,336-scenario result. After all stages are explicitly
authorized and complete, offline `--full` analysis exports 24×1,336 probability
matrices, the separate baseline vector, A/B/C 24×24 normalized and summed-L1
matrices, exact provenance, per-scenario contributions, rankings, prompt effects,
and descriptive subsampling sensitivity (seed 20261022). It refuses an incomplete
grid. Subsampling only describes stability within the analyzed scenario set;
constitution-pair correlations are descriptive because the pairs are dependent.

Required completion checks: every primary and baseline task valid; both answer
logs finite; exact hashes/provider/model; all probabilities in [0,1]; no duplicated
tasks; canaries within tolerance; failed attempts and all costs reconciled; no
unknown in-flight charges; matrix symmetry/zero diagonals/nonnegativity; correct
N scaling; A versus B distinction/Jensen check; all final exports tied to the
same frozen manifest. No historical philosophical-fidelity claim is upgraded by
completion of these engineering checks.
