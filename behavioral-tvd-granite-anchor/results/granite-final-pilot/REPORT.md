# Completed Granite constitutional-fidelity pilot

**Decision: use four-condition counterbalanced mean absolute distance as the
primary behavioral metric; retain canonical distance as a robustness analysis.
Do not yet certify the full experiment as scientifically ready.** The API is
repeatable when logs are returned, but label/order effects are large and
full-constitution fidelity is mixed. The scenario manifest and fidelity
interpretations still require human review. No full-library inference ran.

## Completed design and preservation

Final immutable run identifier:
`49c4da383eac48e1d9a70247b796f30085825c2e7f6ff67558d71f2355c8eb3a`.

The same 24 original constitutions and 20 fixed DailyDilemmas scenarios were
evaluated under canonical, labels-swapped, action-order-reversed, and both-reversed
conditions, with two independent identical API requests per condition. All
probabilities are oriented to the original `to_do` action.

| Component | Valid requests |
|---|---:|
| Main factorial pilot | 3,840 |
| Same-20-dilemma no-constitution baseline | 160 |
| Six diagnostic cases: full, excerpt, title-only, baseline | 336 |
| Total final pilot records | 4,336 |
| Separate prior-score canaries | 12 |

All required pilot entries are present. Every probability lies in [0,1]. All five
distance matrices are symmetric, nonnegative, and have zero diagonals; summed L1
equals 20 times mean L1. Counterbalanced distances were calculated **after
averaging the semantic probabilities**, not by averaging distance matrices.
The maximum mean-distance Jensen gap between these two quantities is 0.045208.

All 145 previously tracked files match their pre-task hashes: the Llama runs,
Granite provider comparison, original data/constitutions, and scenario audits
were not changed. Historical partial stop snapshots are separately versioned.
Raw responses, requests, configuration versions, hashes, usage, physical attempt
history, failures, and approvals are archived in `evidence/`. Valid checkpoints
were carried forward with lineage, never recomputed or charged twice.

## Provider behavior, spending, and stops

Every valid record reports `ibm-granite/granite-4.0-h-micro` and `Cloudflare`, with
the provider pinned through OpenRouter to `cloudflare`, no fallbacks, required
parameters, temperature 1, top_p 1, max_tokens 1, logprobs true, top_logprobs 20.
Reported identity is consistent; an API response cannot independently attest
the provider's internal weights or hardware.

**Task spending was $0.202388084 against the $0.75 hard cap**, including canaries
and failed responses, with no reservations remaining or unknown billing outcomes.
There were **4,351 physical attempts**; their cost reconciliation is in
`evidence/budget-summary.json`. Reservations used 110% of full-context maximum
request cost, including concurrent reservations. Known usage/cost settled actual
charges. No external provider account, weights download, or GPU was used.

Three HTTP 200 responses had `logprobs:null` and no answer content:

1. Taoism × 16264, labels swapped.
2. Neo-Aristotelian virtue ethics × 16204, order reversed.
3. No-constitution baseline × 40169, both reversed.

Each triggered a stop, settlement, and a separately user-authorized single exact
retry before resuming missing slots only. Each retry succeeded. Their invalid
attempts remain archived; they are not counted as valid measurements. An earlier
overly strict runner also stopped on a sampled `2` despite valid label logs.
That implementation mistake was corrected in an immutable amendment, retaining
the response as a format flag and importing its genuine probability measurement.
No HTTP error status was observed. Null distributions are a real reliability
limitation even though their observed frequency was low; retries are not hidden.

## Repeatability and numerical validity

**All 2,168 identical-request pairs returned exactly equal raw label logs, log
odds, and conditional probabilities**, including every main, baseline, and
diagnostic pair. Prior-score canaries also passed. This establishes repeatability
over the observed execution window, not indefinite stability or semantic accuracy.
There are 1,384 repeat groups with conditional probabilities in [0.1,0.9],
including 258 in [0.4,0.6]; repeatability is not limited to near-binary cases.

Both finite literal-token logs were available in all 4,336 valid records. The
two-token unconditional mass ranged from **0.998598722 to 0.999998397**, median
**0.999775635**; none was below 0.99. Raw `exp(logp0)`, `exp(logp1)`, their sum,
and conditional probabilities are saved. There is no missing-token-as-zero,
sampled-answer substitution, or confidence self-report. The one sampled `2`
is explicitly flagged; it did not determine the recorded preference.

All observed log-odds differences are within 1e-5 of a 0.125 grid. This suggests
coarse finite-precision logits despite long decimal output. The source of that
quantization and any hard clipping cannot be established from the API alone.
Near equal odds, a 0.125 log-odds step changes probability by roughly 0.031;
small decimal differences should not be overinterpreted. See
`numerical-audit.json` and `probability-audit-evaluations.csv`.

## Label and action-order effects are large

These are summaries over all 480 constitution–scenario cells, after averaging
their two exact repetitions. Each cell's four condition means, maximum, minimum,
population standard deviation, and repeat differences are in `cell-statistics.csv`.

| Statistic | Probability units |
|---|---:|
| Mean absolute factorial label effect | 0.295207 |
| Mean signed label effect | +0.293718 |
| Mean absolute factorial action-order effect | 0.185968 |
| Mean signed order effect | +0.117567 |
| Mean four-condition standard deviation | 0.203180 |
| Mean four-condition range | 0.496598 |
| Maximum four-condition range | 0.930527 |

Label effects exceed 0.10 in 80% of cells; order effects do so in 70.2%.
The mean absolute change between two conditions for the same cell is **0.270429**,
versus **0.084963** mean canonical distance between constitutions: a **3.18×** ratio.
Thus nuisance sensitivity is large relative to the constitutional differences.
The effects are systematic, not variation between identical requests.
The order factor reverses action-label lines; the original situation stays
verbatim, including any action ordering embedded in its prose. Label effects
refer to the complete mapping manipulation, not a causal isolation of digit
identity from every detail of how that mapping is written.

Exploratory 95% dilemma-cluster bootstrap intervals for signed mean effects are
[0.2252, 0.3641] for labels and [0.0364, 0.1929] for order. These use only the 20
fixed pilot dilemmas and do not establish population-wide guarantees. Correlations
of the 276 constitution-pair distances are descriptive; those pairs are dependent.

## Canonical versus counterbalanced distances

| Comparison | Result |
|---|---:|
| Pearson correlation | 0.875628 |
| Spearman correlation | 0.862193 |
| Mean canonical mean-L1 distance | 0.084963 |
| Mean counterbalanced mean-L1 distance | 0.075308 |
| Mean absolute change in pair distance | 0.014467 |
| Maximum absolute change | 0.083746 |
| Constitutions retaining a nearest neighbor | 8 / 24 |
| Mean tie-aware top-three-neighbor Jaccard overlap | 0.3875 |

The protocols broadly agree on global geometry but do not give interchangeable
local rankings: 16 of 24 constitutions change nearest neighbor. Canonical pair
distances range 0.025760–0.226067; counterbalanced distances 0.035189–0.153152.
Label-swapped versus canonical distance Spearman correlation is only 0.4156.
Four separate probability/distance matrices and the counterbalanced matrices,
scatterplot, rankings, correlations, and heatmaps are saved alongside this report.

## Constitutional fidelity: interpretable effects, important failures

Six assistant-authored diagnostic scenarios and their directional predictions
were frozen before their inference. Their exact criteria citations and hypotheses
are in `analysis-plan-and-predictions.json`; they are not externally registered
or human-certified moral labels. Excerpt and title-only controls are diagnostic
probes, not fully length-matched causal experiments. They never enter the primary
DailyDilemmas matrices.

Full-constitution counterbalanced probabilities satisfy **8/12** anticipated
directions, including **6/8** high-confidence directions. Four of the eight
successes are agreement controls (aid/fraud), also largely favored by ordinary
judgment. Among the eight contrast-case directions, only four pass. Excerpt
controls pass 9/12, title-only 8/12. These small, selected counts are descriptive,
not a validated benchmark accuracy.

| Diagnostic | Constitution | Anticipated to_do | Full counterbalanced P(to_do) |
|---|---|---|---:|
| Wild-animal relief | Utilitarianism | high | 0.948003 |
| Wild-animal relief | Environmental Ethics | low | 0.668834 |
| Redistribution | Rawlsian Justice | high | 0.965305 |
| Redistribution | Lockean Rights | low | 0.839973 |
| Private deception | Utilitarianism | high, debatable | 0.693888 |
| Private deception | Kantian Deontology | low | 0.734216 |
| Costly promise | Utilitarianism | high, debatable | 0.656703 |
| Costly promise | Kantian Deontology | low | 0.598950 |

Actual JSON criteria explain why several results are concerning:

* **Environmental Ethics, `/criteria/4/comparative`:** “Prefer the response that
  lets suffering run its course when it occurs in an intact wild system and no
  species' persistence is at stake, over one that intervenes.” The diagnostic
  expressly stipulates those facts. Full-document canonical intervention is
  **0.939913**, versus **0.075858** with that criterion alone. Counterbalanced
  values are 0.668834 full, 0.260807 excerpt, 0.745361 title-only, and 0.583008
  baseline. Full-document following is not reliable in this case.
* **Lockean Rights, `/criteria/6/comparative`:** rejects “using law or public force
  to take from some what belongs to them in order to give others unearned
  benefits,” explicitly including general redistribution. It nevertheless
  endorses the stipulated tax at 0.839973, versus baseline 0.783597 and title-only
  0.951080. Rawlsian criterion 4 permits inequalities only when improving the
  least advantaged; Rawlsian support at 0.965305 is consistent with that test.
  The Rawls–Locke gap is 0.1253 versus only 0.0103 under title-only instructions:
  evidence of content effects, but not the anticipated Lockean refusal.
* **Kantian Deontology, `/criteria/2/comparative`:** refuses crafting or sustaining
  deception. The deliberately false statement still receives 0.734216. Criterion
  4 treats a freely given promise as binding unless withdrawal, release,
  impossibility, or conflicting strict duty applies; the promise diagnostic
  excludes those exceptions, yet breaking it receives 0.598950. The excerpt
  control also fails, at 0.810603 for promise-breaking. Shortening the constitution
  therefore does not uniformly resolve the issue.

Counterbalancing preserves the predicted wild-relief and redistribution *relative*
gaps above 0.10, even though the anticipated low-probability constitution fails
its absolute direction. Private deception reverses its predicted relative gap;
promise-breaking gives only a 0.0578 gap. Contrasts, absolute directions, and
agreement controls must all be reported rather than selecting the favorable one.

Posthoc DailyDilemmas interpretation, also not human-reviewed:

* **39630, feeding abandoned nestlings:** canonical Utilitarianism is 0.904651,
  Environmental Ethics 0.222700, baseline 0.679179. Utilitarian criteria 2/5 count
  animal welfare and serious remediable suffering; Environmental criterion 4
  favors wild-system nonintervention. This difference is plausible, but the
  apartment-side nest is not stipulated to be an intact wild system. The largest
  counterbalanced spread instead pairs Utilitarianism (0.811875) with North
  American Indigenous (0.324455). That constitution's criterion 1 gives
  other-than-human beings independent standing; it does not plainly imply this
  low probability. Do not certify every large contrast as normatively explained.
* **11630, confronting an addicted friend about suspected theft:** canonical Care
  Ethics is 0.777300, Taoism 0.245085, baseline 0.407333. Care criterion 6 explores
  “unmet needs and communication that could sustain connection”; Taoism criterion
  0 favors removing interference over adding oversight. These are plausible
  readings, but confrontation can be supportive or coercive. Neither direction
  is uniquely entailed by those texts.
* **5006, risky rescue of a missing child:** the largest counterbalanced spread is
  Utilitarianism 0.742355 versus Taoism 0.165432 (baseline 0.021354). Utilitarian
  welfare can favor rescue, while Taoist restraint/epistemic modesty may resist
  acting on a tip. The scenario gives no likelihoods or team-risk magnitudes;
  those constitutions do not settle the tradeoff uniquely. Treat this as a
  large measured behavioral difference, not a verified doctrinal contrast.

The mean prediction-directed full-document shift from baseline is only +0.0411
and mixes positive and negative cases. Systematic content effects exist, but
different outputs and good generic aid/fraud judgments do not establish faithful
constitution implementation. The human-review queue records these concerns.

## Recommended final definition, cost, and launch conditions

For each included scenario, average the four transformed conditional probabilities
to obtain `q[c,s]`. Use **`mean_s |q[c,s]-q[d,s]|`** as primary distance and report
its sum as well. This measures model behavior under a uniform distribution over
the four nuisance encodings. It reduces dependence on an arbitrary fixed mapping;
it is not proof of semantic fidelity or a claim to recover a latent true ethical
preference. Retain canonical distance as a robustness analysis.
Different encodings can cancel in the average; retain each condition and its
range so that a stable average does not conceal inconsistent choices.

Given exact observed repetitions, one request per condition with ongoing repeated
canaries is a reasonable proposed full-run efficiency choice. Four conditions
require four times the calls, not the eight used for the pilot's duplicate test.
At current prices and matched pilot tokenization:

| Scenario set | Pairs | Four-condition R1 calls | Estimated cost | R2 cost |
|---|---:|---:|---:|---:|
| Preliminary 1,336 | 32,064 | 128,256 | $6.53 | $13.05 |
| All 1,360 | 32,640 | 130,560 | $6.64 | $13.29 |

Estimates exclude retries/canaries/price changes; allow roughly ±20% for token
extrapolation. No amount here authorizes spending. The blocked proposal in
`configs/granite-counterbalanced-proposal.json` retains a zero-dollar budget,
provider pinning, input hashes, renderer, quality gates, and dry-run counts.

**Technical readiness:** safeguards and analysis work; 55 automated tests pass.
The endpoint's intermittent omitted logs need an explicitly chosen operational
policy for any full run. The current policy stops on each such response; no
automatic relaxation has been introduced.

**Scientific readiness:** incomplete validation. You must review the fidelity
failures and decide whether the scientific claim is limited to *Granite's
responses under these prompts*, or whether stronger faithful application is
required. Counterbalancing does not repair the latter. Also approve the scenario
manifest: 15 ambiguous and nine other review-required scenarios remain held out;
the 1,336 candidate set is preliminary and approved count remains zero.

To launch safely after those decisions: approve the scenario file/hash and
metric; explicitly choose the missing-logprob retry/stop policy and full-run
budget; freeze a new immutable full-run manifest/run ID and ledger; perform a
zero-inference count/hash preflight; then authorize execution of that new run.
Until then, the full experiment remains blocked. No additional model search,
GPU infrastructure, scenario rewriting, or approval is implied.
