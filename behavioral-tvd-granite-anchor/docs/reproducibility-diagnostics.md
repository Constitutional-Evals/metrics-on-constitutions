# Same-model probability reliability diagnostic — 2026-10-20

Decision: do not launch the full experiment or approve the candidate scenarios. The application-side extraction is sound in the examined records, but the hosted endpoints tested do not establish a sufficiently reproducible fixed-prompt probability measurement. No identifiable evidence supports assigning the fault specifically to FP8.

## Evidence and preservation

Pre-existing commit: `8f1dab0ea6254b638afaea7dcfa99bef19e4ffda`. SHA256 checks confirm the completed 480-cell pilot, prior reliability responses, candidate scenario file and approval manifest are unchanged (`results/repro-diagnostics/prior-preservation.json`). No existing experimental model/provider/configuration was changed. All new inference used isolated study identifiers and a new shared $1 ledger at `/workspace/work/repro-diagnostics-2026-10-20/budget.sqlite`, using the existing reservation/settlement safeguards. No hidden retries. Five HTTP 429 attempts were explicitly recovered once in new studies, preserving the original failures; recovery timing is a confound.

Versioned `results/repro-diagnostics/` contains selection, all 428 valid raw response/request records in `raw-evidence.jsonl.gz`, study specifications and attempts including invalid/error evidence in `study-manifests.json.gz`, per-response log probabilities/log-odds, hashes, usage and metadata in `evaluations.csv`, repeat-group statistics, earlier complete anomaly responses and generation metadata, distance sensitivity, tests and summaries. Gzip JSONL is readable with Python gzip; no external proprietary reader needed. Separate backup: `/workspace/backups/repro-diagnostics-2026-10-20.tar.gz` and SQLite snapshot. SHA256 inventory accompanies the versioned evidence.

Reported response charges: **$0.34172309** (428 valid plus one invalid response). Five 429 outcomes have no returned usage/cost; conservatively retaining their full reservations adds $0.15859987, for **$0.50032296 accounted**, below $1. There were 434 paid-endpoint attempts, with no outstanding reservations. Free endpoint catalog/generation metadata GETs are separate. Actual 429 billing cannot be proven from response usage. No full run or scenario approval occurred.

## Earlier Conservatism × 16204 anomaly

The three complete saved responses share canonical request hash `d7cce5ee8cb981cb1c01bbb251dac18ce1d3ecd14b9d5962877dbf7ef3933801` and prompt hash `2f46e4033be2b8bf0e0bff350b3d8333bb64c078d91370cf99bbff55d18276d5`. System/user messages and ordering are identical. Each reports 3,062 prompt tokens, one completion token, requested model `meta-llama/llama-3.3-70b-instruct`, provider Parasail, and no system fingerprint. Endpoint selection explicitly allowed only `parasail/fp8`, disallowed fallbacks and required parameters.

| Response ID suffix | logp(0) | logp(1) | log odds 1/0 | conditional p(1) | sampled | cached tokens |
|---|---:|---:|---:|---:|---|---:|
| I9db0IFEk6zA2115CGQ5 | -0.000552978192 | -7.500553131104 | -7.500000153 | .000552779 | 0 | 160 |
| X4xw6OnMavqQk4QRfSsZ | -.825939416885 | -.575939416885 | .25 | .562176501 | 0 | 2,992 |
| hEPi09sDTp6jJirs6vWb | -.313261657953 | -1.313261628151 | -.999999970 | .268941427 | 1 | 3,040 |

Full IDs, timestamps, all top-20 entries, bytes, usage, costs and metadata are retained in `earlier-anomaly-raw.json`. Generation lookup supplies distinct upstream `chatcmpl-*` IDs but no GPU, immutable weight hash, numerical configuration or backend instance identity. Those are request IDs, not evidence of different machines. Generation metadata says streamed=true while the client did not request streaming; it does not establish a change in mathematical input.

The top-logprob list is not always sorted by probability: the sampled token can appear first. Extraction identifies exact strings `0` and `1` (ASCII bytes 48 and 49), never list positions or sampled-token identity. Sampling the lower-probability answer is entirely consistent with T=1. Independent exp/normalization reproduces stored probabilities; the discrepancy already exists in the raw log-odds. It is not an underflow, sigmoid, normalization, token-label, or sampled-response substitution error. A 7.75 log-odds shift is far beyond rounding these two returned floats.

Identical saved client payloads rule out application message construction differences for these records; new diagnostics also preserve the SHA256 of actual serialized request bytes and safe response headers. Reported routing rules out an observed provider/model switch, but cannot establish immutable weights/templates or enforcement of every upstream setting. Plausible causes include provider batching/kernel choices, caching implementation, load-dependent execution, model/template revisions or coarse upstream logits; none is identified causally. Cache counts differ and merit investigation, but correlation is not proof. FP16 also varies, contradicting any simple FP8-only explanation.

## Controlled repeats

Selection is fixed: all 13 pilot cells with .1 < p < .9, plus three lowest and three highest cells (ties constitution then numeric dilemma ID). Exact pairs/IDs and hashes are in `selection.json`. Main settings remain T=1, top_p=1, max_tokens=1, logprobs=true, top_logprobs=20, same original messages and ASCII answer tokens. Each of 19 pairs has three valid repeats in each condition. Explicit supported seed: 20261020. Workers: 1 or 4. Endpoint metadata advertises seed support; the client refuses seed tests otherwise. Main phase order was sequential/no seed, concurrent/seed, concurrent/no seed, sequential/seed, with reproducibly shuffled items. This is a diagnostic, not a randomized causal estimate of concurrency effects; endpoint load and phase time remain uncontrolled.

| Parasail condition | valid | nonidentical groups /19 | median within-pair range | maximum range |
|---|---:|---:|---:|---:|
| sequential, no seed | 57 | 19 | .108599 | .551190 |
| concurrent, no seed | 57 | 18 | .086516 | .670972 |
| sequential, fixed seed | 57 | 19 | .138396 | .941587 |
| concurrent, fixed seed | 57 | 19 | .164439 | .747988 |

Mean absolute differences between the 19 phase-specific cell means: sequential/concurrent .077373 without seed and .114872 with seed. These are observed differences, not isolated concurrency effects. A seed demonstrably does not guarantee reproducibility or consistently improve it here.

Focused Conservatism × 16204, 12 repeats per condition:

| condition | p range | mean | SD | log-odds range |
|---|---|---:|---:|---:|
| sequential, no seed | .000553–.562177 | .075048 | .156013 | 7.75 |
| sequential, seed | .000553–.562177 | .109843 | .171540 | 7.75 |
| concurrent, no seed | .010987–.222700 | .089192 | .065822 | 3.25 |
| concurrent, seed | .017986–.148047 | .062975 | .045730 | 2.25 |

Three short controls (true arithmetic, false arithmetic, unrestricted choice of 0/1) × three repeats × four conditions gave 36 valid responses. Maximum within-group p range was .000003242. All were saturated, including the neutral-choice control: this is not evidence of balanced answer preference. It supports an association between these long/content-rich prompts and greater conditional-probability variability, but does not isolate length: content and probability sensitivity also differ. Near saturation a large log-odds change can yield a tiny p change. A subsequent causal diagnostic should pad/trim a fixed task and control its decision margin.

## Alternative providers, same named model

Each explicitly pinned endpoint used no fallbacks, required all parameters, and the identical messages/T/top_p/top-logprob settings. Different provider-specific price caps are operational metadata, not intentional sampling changes. No alternative was substituted into the old pilot.

* **CoreWeave `coreweave/fp16`:** advertised FP16; 115/115 responses had both labels (one probe plus 114 comparison requests). Model/provider names consistently matched. Three repeats of all 19 pairs: sequential median range .001150, max .138396; concurrent median zero, max .042100. Nonidentical groups 16/19 and 6/19 respectively. Conservatism sequential range .320821–.437823, concurrent .320821 throughout three repeats; isolated earlier probe .268941. This is better observed repeatability, not a validated stable replacement. Mean absolute difference between CoreWeave sequential and Parasail sequential cell means was .123901 (max .607081); backend changes can change the scientific measurements as well as noise.
* **Novita `novita/bf16`:** advertised BF16; initial probe returned both labels, p=.851953. The next comparison request returned HTTP200 with `logprobs:null` despite required parameters. It was stored invalid and the capability gate stopped the batch. Not a reliable logprob backend under this test. No probability imputed and no fallback.

Precision names are catalog claims, not audited weight checksums or full precision arithmetic guarantees. Same model ID does not prove identical effective weights or chat templates. There is no scientific basis to equate provider differences with precision effects alone.

## Saturation and precision

Independently recomputed all original 480 conditional probabilities directly from raw logs: maximum discrepancy 5.6e-17. **430/480** are within .001 of an endpoint, **13/480** strictly between .1 and .9; the remaining 37 lie between those bands. For the saturation criterion, |logp1-logp0| >= log(999) ≈ 6.906755 is sufficient. Returned logs support the saturation; it is not caused by assigning missing labels zero or by underflow.

All six selected extreme cells remained saturated in all 72 Parasail main repeats and all 36 CoreWeave comparison repeats. CoreWeave had 21/57 saturated responses per condition across the deliberately middle-enriched 19-pair sample; that fraction must not be extrapolated to all 480 cells. Thus substantial saturation survives another endpoint, but this does not certify calibrated ethical confidence. Conditional mass renormalization measures answer preference, not real-world confidence or robustness to prompt changes.

For long selected prompts, returned P(0)+P(1) was ~0.999999934–1.000000058 across Parasail and CoreWeave (tiny excess over one is float rounding). Both labels were returned in every valid diagnostic response; the Novita null response was explicitly invalid. Many log-odds lie on a coarse grid (frequently quarter/eighth increments), and equal probability plateaus recur across endpoints. This is consistent with coarse logits somewhere upstream but does not identify a dtype/kernel or prove clipping. No forced-zero/one substitution or known hard clipping was found. Hosted top-20 lists cannot prove the full-vocabulary normalization or pre-processing implementation; direct logits are the stronger reference.

## Consequences for the metric

The fixed-prompt target is p=sigmoid(logp1-logp0). Repeated hosted requests here are not a single demonstrated deterministic evaluation of it. A single request is unreliable for some decision-margin cases, even though many saturated cases are stable. Numerical variation (identical input), prompt sensitivity (changed input), and between-constitution behavior are separate quantities. A provider switch is an additional measurement condition and requires new run IDs and validation.

For mean absolute distance D(c,d)=sum_i |p_ci-p_di|/N, errors satisfy |Dhat-D| <= sum_i(|e_ci|+|e_di|)/N. Summed L1 is N times the mean. A .562 probability range at one cell can alone move a 20-scenario distance by .0281; the largest observed .942 range gives .0471. Dividing by 1,336 dilutes a single affected cell to .000705, but the affected-cell frequency/correlation is unknown, so this does not justify assuming the full run will average out.

A fixed-seed 1,000-draw sensitivity demonstration resampled only the 19 cells from their three sequential/unseeded measurements and held all other 461 cells fixed. The Kantian–North-American-Indigenous mean distance had a central empirical span .118381–.190144 (width .071762). See `partial-distance-sensitivity.json` for all 276 pairs. This is not a confidence interval: three repeats poorly identify a distribution, errors may correlate, recoveries occurred later, and most cells were held fixed. It shows possible material effects even under restricted perturbations.

Independent unbiased errors shrink approximately as SD/sqrt(R); systematic shifts, correlations, backend mixtures and template effects do not. For the focused sequential anomaly SD≈.156, three-repeat mean SE≈.090, 12-repeat SE≈.045; achieving a nominal .01 95% half-width would require ~935 independent repeats if this SD persisted. That extrapolation is illustrative, not a validated sample-size prescription. Absolute distances can have positive noise bias even when underlying probabilities coincide. Replicate means should be formed before computing absolute distances, with uncertainty propagated and rankings tested.

Counterbalancing label association and action order defines a new estimand: average the appropriately transformed to_do probability across four predeclared equally weighted prompt conditions, then compute distances between those averages. It can reduce some label/order dependence but does not guarantee bias cancellation or numerical reproducibility. It differs from averaging four distance matrices because absolute value is nonlinear. Replication within each condition is still needed; uncertainty and condition interactions must be reported. Earlier label/order effects remain evidence of real prompt dependence, not evidence that identical requests should vary.

## Deployment and practical choices

| option | reliability and interpretation | approximate candidate cost | effort |
|---|---|---|---|
| canonical Parasail, one request | same original estimand, demonstrated instability; not recommended for final inference | $21.24 uncached | low |
| canonical CoreWeave FP16 | considerably better but still fails strict repeatability; backend-specific probabilities | $68.51 uncached | low–moderate; new validation/run |
| controlled local direct logits | strongest control over weights/template/hardware; can inspect both labels and full normalization, still must validate batching/kernels | hardware benchmark required; examples below | substantial |
| replicated/counterbalanced | estimates a declared average over requests/templates, not necessarily a fixed theoretical forward pass; requires uncertainty | Parasail 3 repeats ~$63.71; four conditions ~$84.95; 3×4 ~$254.86 | moderate–high |

Costs use the unapproved 1,336-scenario candidate, 32,064 evaluations, ~96.464M input tokens and 32,064 output tokens; exclude retries, changed prompt lengths, cache discounts and price changes. CoreWeave catalog price $.71/M input/output; Parasail $.22/M input and $.50/M output. None is a spending authorization. The full 1,360-scenario library would have 32,640 evaluations, but the final scenario count is not approved.

Llama 3.3 70B BF16/FP16 weights require roughly 140–142 GB decimal before runtime overhead. Two 80GB GPUs can support a carefully configured short-context, low-batch reference; four provide more headroom. A single 141GB H200 is too tight to assume; a 180GB B200 has more room. FP8 weights ~70GB and 4-bit ~35GB before overhead change precision, so are not an interchangeable reference. Configuration has 80 layers, 8 KV heads and head dimension128: BF16 KV cache ~.3125 MiB/token/sequence, ~1.25GiB at4,096 tokens. Allow activation/workspace overhead, tensor-parallel communication, weight storage ~150–200GB plus software, and substantial host memory (often192–256GB; loading strategy matters).

A direct Transformers reference should freeze model/tokenizer revisions, exact chat template/token IDs (verify labels0/1 tokenize individually as15/16 for this tokenizer), software/CUDA versions, GPU type, dtype, attention implementation and deterministic settings. Use eval/inference mode and the last-position forward logits without sampling; compute full-vocabulary log_softmax in FP32, extract both label logs, and sigmoid their difference. Verify actual prompt token IDs against the hosted template if parity is claimed; hosted templates are not fully observable. A new local run defines its own fully documented backend.

vLLM improves throughput, but seeded sampling is not sufficient. Official reproducibility guidance requires hardware/version control, deterministic scheduling or batch invariance; online serving needs batch invariance for batch-dependent effects. `VLLM_BATCH_INVARIANT=1` is evolving/beta and must be tested for this exact Llama3.3 model, hardware and release, not assumed from other tested Llama versions. Direct Transformers batch1 is the simpler reference before optimizing.

Indicative advertised Runpod prices: A10080GB $1.79/h; H100PCIe $2.89/h; H100SXM $3.99/h. Two H100s are ~$5.78–7.98/h; a one–two-hour diagnostic could cost ~$6–16 plus setup/storage. No GPU was deployed. Full cost is unknown until benchmarking: at hypothetical aggregate prefill1,000 tokens/s, 96.464M input tokens take26.8h (~$155–214 on two H100s); at5,000/s,5.36h (~$31–43). These are arithmetic scenarios, not measured performance; deterministic kernels, loading, repeated prefixes and concurrency materially affect throughput/cost.

## Recommended next validation, before any full run

Use a pinned **local BF16 direct-forward reference** for the same19 pairs. Do not assume CoreWeave alone fixes the problem. First reproduce tokenization and templates, then obtain30 repeated forward passes/pair at batch1, and30 passes with shuffled mixed batch composition and cache off/on. Save full label logits, FP32 normalized probabilities, token IDs, hashes and hardware/software metadata. Compare stable within-configuration repeats separately from intentionally changed backend/template configurations. No deployment or new spending is authorized by this recommendation.

Predeclare an engineering gate, subject to the investigator accepting these tolerances: for every selected pair, max identical-input p difference <=.001, log-odds difference <=.01; no missing labels/nonfinite logits; identical prompt token hashes; repeat pairwise mean distances stable within .005 on a subsequent complete24×20 validation with repeated blocks. Separately run four label/order conditions on that validation, report interactions, and decide whether the scientific target is canonical or counterbalanced before locking the full configuration. These thresholds are proposals, not previously approved claims of sufficient scientific accuracy. If batch execution fails, use batch1 or validated invariant kernels and benchmark again; do not loosen the gate silently.

The scenario audit remains provisional and unapproved (15 ambiguous,9 other review cases). Review those independently; this diagnostic neither resolves them nor authorizes the full experiment. Proceed only after the numerical validation, estimand decision, scenario approvals, new immutable manifests, cost benchmark and explicit run budget are finalized.

Sources (accessed2026-10-20): [official model card](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct), [vLLM reproducibility](https://docs.vllm.ai/en/stable/usage/reproducibility/), [vLLM batch invariance](https://docs.vllm.ai/en/stable/features/batch_invariance/), [Runpod pricing](https://www.runpod.io/pricing). Architecture fields archived from the public unsloth mirror config; precision/rates/capabilities archived from OpenRouter endpoint metadata, not independent audits.
