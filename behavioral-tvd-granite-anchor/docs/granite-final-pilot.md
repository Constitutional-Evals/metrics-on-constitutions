# Final Granite pilot

This is a separate experiment; the historical Llama experiments, cloud-provider
comparison, constitution files, scenario text, and scenario audit are unchanged.
The findings and methodological decision are in
[`results/granite-final-pilot/REPORT.md`](../results/granite-final-pilot/REPORT.md).
No complete-library experiment was executed or authorized by this pilot.

## Protocol

The main design is 24 original constitutions × the same 20 fixed DailyDilemmas
scenarios × four label/order conditions × two independent requests: 3,840
measurements. Conditions are canonical, labels swapped, action lines reversed,
and both reversed. Their names refer to the original `to_do`/`not_to_do` mappings.
Only the instruction for the constitution varies between constitutions within a
condition. Original situation/action text is preserved; annotation fields are
absent. Exact requests, messages, hashes, returned logs, and usage are archived.

There are also 160 DailyDilemmas no-constitution requests, 336 diagnostic/control
requests, and 12 historical probability canaries. Six assistant-authored diagnostic
scenarios and their anticipated directions were frozen before their inference.
Full constitution, selected exact criterion excerpts, title-only, and
no-constitution variants are controls, not additions to the primary distance
matrix. Predictions and semantic interpretations are automated and require human
review; they are not externally registered or human-certified moral labels.

All requests use `ibm-granite/granite-4.0-h-micro`, pinned to `cloudflare`:
`temperature=1`, `top_p=1`, `max_tokens=1`, `logprobs=true`, `top_logprobs=20`,
`provider.only=["cloudflare"]`, `allow_fallbacks=false`, and
`require_parameters=true`. Price ceilings are $0.017/M input and $0.112/M output
tokens. The schedule is interleaved using seed 20261021, with six concurrent
requests. Exact prior requests were checked before execution; two repeated
requests use identical payloads, not a changed sampling seed.

For literal ASCII token logs `l0` and `l1`, raw probabilities are `exp(l0)` and
`exp(l1)`. Conditional `P(1 | {0,1}) = sigmoid(l1-l0)`. For swapped labels the
semantic `P(to_do | {0,1})` is `sigmoid(l0-l1)`. The mass `exp(l0)+exp(l1)` is
reported separately. Both genuine, finite next-token logs must exist: there is
no imputation, missing-token-as-zero, confidence self-report, or sampled-answer
substitution. A sampled non-label is retained as an instruction-compliance flag
if both required logs are valid.

Let `p[c,s,k]` be the mean of the two semantic repeated probabilities in condition
`k`. Canonical distance is `sum_s |p[c,s,0]-p[d,s,0]|`. The counterbalanced
probability is `q[c,s] = (1/4) sum_k p[c,s,k]`; its distance is
`sum_s |q[c,s]-q[d,s]|`. Mean absolute distance divides either sum by N=20.
The latter is **not** the average of condition-specific distances. The averaged
distance is retained only as a comparison; Jensen's inequality is checked.

Label effect is `(swapped + both - canonical - reversed)/2`; order effect is
`(reversed + both - canonical - swapped)/2`. Cell ranges and population standard
deviations use the four condition means. Descriptive distance correlations use
276 upper-triangle entries, which are dependent. Exploratory confidence
intervals resample the 20 dilemma clusters, retaining constitutions together:
5,000 draws, seed 20261022. They are not population-level guarantees. Ranking
ties are recognized at 12 decimal places without rounding the probability data.

## Checkpoints, budget, and amendments

The new task ledger has a fixed $0.75 lifetime cap. Before dispatch it reserves
110% of the maximum full-context request cost, including other in-flight
reservations. Known costs settle from response usage. Unknown billing outcomes
retain conservative charges. SQLite transactions, WAL, and FULL synchronous
mode protect claims and settlement. Normally resumed valid slots are never
recomputed. Unknown in-flight records cannot be automatically released.

There are at most two attempts per ordinary slot, with bounded exponential
backoff for transient errors. Missing/malformed distributions, wrong identity,
unexpected drift, a failed retry, or three HTTP errors in a rolling 20 outcomes
stop dispatch. Existing in-flight requests settle. Repeated-request tolerances
are 0.001 conditional probability and 0.01 log odds; measured differences are
reported without rounding them to these thresholds.

Five immutable configurations preserve the execution history:

1. `491da222b930…` stopped because the initial runner unnecessarily rejected a
   sampled `2`, despite valid logs for `0` and `1`. This was an implementation
   mistake, corrected without changing scientific payloads or redoing valid
   requests. The response was revalidated and carried forward.
2. `81fb346a7f58…` imported those valid responses and resumed only missing slots.
   It stopped on an actual HTTP 200 response with `logprobs:null` for Taoism ×
   16264, labels swapped. The invalid response and stopped checkpoint remain.
3. `fe190eb8378f…` records the user's explicit approval, "Retry once, then resume
   if valid." The one-attempt gate retried the identical failed request first;
   after valid logs returned it imported all 1,682 completed responses and
   continued only missing slots under the same ledger. Any further substantive
   safety failure would stop again.
4. The second authorized resume carries all 3,271 valid responses forward after
   another missing-logprob stop, this time Neo-Aristotelian virtue ethics ×
   16204 with reversed action order. The user separately approved the same
   one-attempt gate followed by missing slots only; the same ledger and stop
   conditions remain in effect. Neither missing-logprob failure is erased.
5. A third separately approved one-attempt gate follows a missing-logprob
   no-constitution baseline response for 40169 with both labels and ordering
   reversed. It imports 3,488 valid responses and runs only the missing slots
   after a valid gate, retaining the same ledger and stop rules.

Imports carry source attempt/run lineage and incur no inference or second charge.
Count spending from physical attempts, not duplicated imported evaluation rows.
Archived v1/v2 runner implementations explain their configuration hashes.

## Analysis and preservation

Analysis makes no API calls:

```bash
GRANITE_DESIGN_FILE=/workspace/work/granite-final-pilot/design-v5.json \
  PYTHONPATH=src .venv/bin/python scripts/analyze_final_granite_pilot.py
PYTHONPATH=src .venv/bin/python scripts/check_final_granite_numerics.py
.venv/bin/python scripts/verify_final_granite_artifacts.py
.venv/bin/python -m unittest discover -s tests
PYTHONPATH=src .venv/bin/python scripts/preserve_final_granite_pilot.py
```

The versioned evidence contains complete compressed immutable configurations,
raw final responses, attempt history (including failures), canaries, prospective
predictions, authorization, and execution snapshots. The ignored operational
SQLite ledger is additionally backed up outside the repository. A SHA-256
inventory covers report artifacts. Prior tracked files are compared to their
pre-task hashes; earlier experiment evidence is never overwritten. The partial
stop snapshot is retained separately and must not be mistaken for final results.
The later stop snapshots are likewise preserved in
`results/granite-final-pilot-stop2/` and `results/granite-final-pilot-stop3/`.
The final pilot completed all 4,336 planned records under design v5 after the
three separately approved gates. Total task spending was $0.202388084.
Its final run ID is
`49c4da383eac48e1d9a70247b796f30085825c2e7f6ff67558d71f2355c8eb3a`.

Do not run the preparation/resumption scripts to launch a full experiment: they
are the historical pilot procedures. A future full run requires an explicit
decision about scientific fidelity, human approval of the scenario manifest,
a new frozen full-run configuration and identifier, and an explicit budget.
No script in this change approves held-out scenarios or launches that run.
