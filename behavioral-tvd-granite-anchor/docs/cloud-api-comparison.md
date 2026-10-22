# Cloud API comparison and recommendation — 2026-10-20

**Recommendation: `ibm-granite/granite-4.0-h-micro` through OpenRouter, pinned to `cloudflare`.** It is an instruction-tuned open-weights model (~3.2B parameters, Apache2.0), accessible using the existing OpenRouter key. No GPU provisioning, model download, additional credentials or subscription is needed. It was the only tested combination to pass the provisional probability/log-odds reproducibility criteria across the complete main dataset. Use it for the next cloud pilot; scientific suitability of a small model still needs review before finalizing the full experiment.

No full experiment was launched. All pre-existing tracked files, prompts, configurations and evidence match their pre-study hashes. Only new study files/configuration/report were added. No other provider account was charged.

## Protocol

The common screen/main dataset is the exact frozen 19 constitution–dilemma pairs from the prior diagnostic: 13 intermediate-probability Llama70B pilot cases plus 6 extreme controls. Source `data/local-validation/diagnostic19.json` is merely a historical file location; this study uses no local model. Selection IDs, prompt hashes and protocol are archived in `results/cloud-api-comparison/`. All existing messages and their ordering remain unchanged. Original paired action labels remain1=to_do,0=not_to_do; no values/consequence annotations were introduced.

Each candidate was pinned explicitly with `provider.only`, `allow_fallbacks:false`, `require_parameters:true` and endpoint-specific price ceilings. Settings: temperature1, top_p1, max_tokens1, logprobs=true, top_logprobs20; seed unspecified. Granite 4.2 alone had reasoning explicitly disabled, as a separately recorded parameter. Capability probes gated the screen/batch. Catalog support was never treated as proof.

Eight combinations underwent main repeated studies:3 identical requests/pair at client concurrency 1 and 3 at concurrency 3, nominally 114 requests/combination. Ten main requests failed with 429 (8 NeMo,1 QwenGoogle,1 QwenParasail), explicitly missing. Screen/probe errors are additional. Fixed request-order seed 20261020. Phases were sequential then concurrent; this is a controlled client-setting comparison, not a causal isolation of concurrency from time/server traffic. There is no control over provider-global batching/load. Models added after discovery used the same frozen 19-pair dataset; extensions and selection rationale are in `protocol.json`.

The prior provisional engineering thresholds (.001 maximum conditional-probability range and .01 maximum log-odds range) were retained for comparison. These are not universal scientific accuracy standards. Raw logs and both unconditional probabilities are preserved. The primary metric is stable sigmoid(logp1−logp0), equivalent to exp(logp1)/(exp(logp0)+exp(logp1)). No logit bias, forced-answer grammar, altered temperature, sampled-answer proxy, missing-token zero or confidence elicitation was used.

Every valid result required literal next-token0 and1 entries with finite logs, matching token bytes where supplied, and consistent token usage/cost. Returned model/provider identities were checked. Non-digit sampled outputs are recorded separately as format failures, rather than silently replacing their probabilities or discarding valid token distributions. NeMo had3 such outputs; the recommendation had none.

## Main comparison

Rates are USD per million input/output tokens. Cost estimates are for 32,640 evaluations (24×1360), canonical one-token answers, uncached, with roughly±20% extrapolation uncertainty, excluding retries/price changes. They scale the prior full-token estimate by observed matched-prompt tokenization ratios. The1336-scenario candidate remains unapproved; its 32,064-evaluation cost is slightly lower. No price quote is spending authorization.

| Model | Pinned endpoint | Size | Rate input/output | Context | Screen intermediate / valid | Max repeat p range sequential / concurrent | Estimated full cost |
|---|---|---|---|---:|---:|---|---:|
| **Granite 4.0 H Micro** | **cloudflare** | **3.2B** | **.017 / .112** | **131,000** | **18/19** | **0 / 0** | **$1.66** |
| Llama 3.1 Instruct | coreweave/bf16 | 8B | .22 / .22 | 131,072 | 19/19 | .030490 / .030490 | $21.61 |
| Llama 3.1 Instruct | novita/fp8 | 8B | .02 / .05 | 16,384 | 19/19 | .091250 / .123876 | $1.97 |
| Granite 4.2 (reasoning off) | coreweave/bf16 | 8B class (~8.8B) | .10 / .15 | 131,072 | 7/19 | .001666 / .030967 | $9.90 |
| Mistral NeMo Instruct | io-net/fp16 | 12B | .01656 / .0216 | 128,000 | 18/19 | .079704 / .054430 | $1.64 |
| Gemma 3 IT | nextbit/fp8 | 27B | .08 / .35 | 131,072 | 2/19 | .670601 / .001016 | $7.63 |
| Qwen3-Next Instruct | google-vertex/global | 80B total / ~3B active | .15 / 1.20 | 262,144 | 2/19 | .593147 / .117002 | $14.73 |
| Qwen3-Next Instruct | parasail/fp8 | 80B total / ~3B active | .10 / 1.10 | 262,144 | 2/19 | .168882 / .168882 | $9.83 |

The8B/12B/27B/80B endpoints all expose actual answer-token log probabilities in valid responses, but none passed the retained numerical criteria on every tested pair. NeMo's concurrent phase had49/57 valid responses; the two Qwen sequential phases each56/57. Other main phases57/57. Median ranges and per-pair values are in `repeat-groups.csv`; maxima alone do not describe every case.

Maximum log-odds ranges (sequential/concurrent): Granite Micro0/0; LlamaCore.125/.125; LlamaNovita.375/.500; Granite 4.2 .250/.250; NeMo.375/.250; Gemma5.50/4.50; QwenGoogle4.00/1.25; QwenParasail2.00/2.00. Thus small p changes near saturation do not by themselves establish numerical stability. Eighteen of Granite Micro's 19 screen cases were intermediate (.1<p<.9), so its repeatability is not an artifact of testing only near-zero/one probabilities.

Catalog precision labels (BF16/FP16/FP8/unknown) are not audited numerical execution guarantees. The recommended Cloudflare endpoint's precision is **not disclosed**. BF16/FP16 endpoints also varied; these data do not identify precision as the cause.

## Additional candidates rejected by live checks

| Candidate | Catalog support / rate | Observed result | Limitation |
|---|---|---|---|
| Qwen3-30B-A3B-Instruct-2507 / dekallm | 30.5B total /3.3B active; .09/.30;262144 context | Both explicit capability attempts429 | No measured probability reliability; hypothetical full cost~$9 only |
| Mistral Small3.2 24B / parasail/bf16 | .09/.30;131072 context |11 valid responses,10 rate-limit errors across probe/retry/screen | Both labels available when successful; availability too poor to proceed with repeat comparison; estimated full cost~$9 |
| Llama 3.2 3B / cloudflare | .0509/.335;80000 context | HTTP200, `logprobs:null` | Sampled answer is insufficient; gate stopped all further calls; hypothetical full cost~$5 |
| Mistral Small3.1 24B / cloudflare | .351/.555;128000 context | HTTP200, `logprobs:null` | Gate stopped; hypothetical full cost~$35, not a qualified option |

These checks covered12 combinations/10 model identities. Endpoint support must be tested **per model**, not assumed from another model on Cloudflare. Likewise `require_parameters:true` does not repair incorrect capability advertising. No fallback was used. Together/Fireworks were not charged or used: existing OpenRouter access yielded a working option without requiring another account.

All listed weights are publicly available instruction/chat models. Granite/Qwen/Mistral metadata specifies Apache2.0; Llama and Gemma use their own open-weights licenses. Source model-card metadata (including parameter counts, license and repository SHA) is archived in `weight-provenance.json`; repository SHA does not prove the immutable revision served by a hosted endpoint. No weight files were fetched.

## Stronger check of the recommendation

Granite Micro produced **326/326 valid responses**, all with both label logs, correct model/provider identity and one-digit output. This includes1 probe,19 screen,114 main repeats,120 confirmation repeats and72 constitution-coverage requests.

The 6 confirmation pairs were frozen from screen probabilities:4 closest to.5 plus low/high tails, selected before new confirmation calls:

- Environmental Ethics×11630
- Neo-Aristotelian Virtue Ethics×16264
- Kantian Deontology×16264
- Taoism×40169
- Taoism×25416
- Care Ethics×16264

Four blocks used sequential/concurrent/concurrent/sequential execution,5 repeats/pair/block (20 fresh measurements/pair). Maximum variation was **zero** for conditional probabilities, individual logp0/logp1 and their differences, across all identical-prompt records in all phases. Serialized request-body hashes are identical per pair. All 326 response IDs are distinct; sampled outputs include198 zeros and128 ones, while underlying recorded probabilities remain unchanged. The application did not cache/substitute results. Provider-side caching cannot be ruled out; the tested claim is observable API repeatability, not proof about uncached GPU kernels.

Example genuine distribution entries for Environmental Ethics×11630:

- logp0=logp1=−.69354647397995
- unconditional P0=P1=.4998003931435019
- conditional P1=.5
- P0+P1=.9996007862870038

Conservatism×16204: logp0=−.3488616347312927, logp1=−1.2238616943359375, conditionalP1=.2942149597859341. These values repeated exactly; they are not self-reported confidence. Across all 326 responses, binary mass ranged .99919798–.99989932. Other next tokens retain a small nonzero mass; conditioning is therefore explicit, not assumed.

All 24 original constitution prompts were evaluated on the same 3 existing dilemmas16204,3385,5070. All 72 requests succeeded with both labels. Prompt lengths were 2571–3728 tokens; all 24 resulting probability vectors were distinct. Between-constitution probability spreads were.282191,.235722,.397660 for the three dilemmas respectively. This demonstrates usable input lengths, output-format compliance and nontrivial constitution-associated variation. It **does not prove faithful interpretation of every ethical principle**, and three scenarios are insufficient to validate semantic quality. A 3.2B model is less capable than the larger alternatives in general; that tradeoff must remain explicit.

The separate24×3 probability and summed/mean-L1 matrices are included. They are diagnostic outputs, not the old24×20 pilot or the full experiment. MeanL1 divides by3 in these files. No old results were overwritten or mixed.

Gemma's largest discrepancy occurred under the **same** returned backend fingerprint. Two fingerprints appeared overall, but that does not explain or isolate the instability. Other providers generally supplied no useful fingerprint. The scientific target is the pinned API model/provider's conditional distribution, not proven identity with locally downloaded weights.

## Spending, engineering and recommendation

One shared persistent **$1** SQLite ledger reserved full-context maximum cost plus10% before every dispatch, including concurrent reservations. Usage/cost settled completed responses. No automatic retries. The two initial429 capability failures each received one explicit retry in distinct preserved studies; later errors were kept missing. No valid old evaluations were recomputed.

- 1265 valid inference responses.
- 2 invalid HTTP200/null-logprob responses.
- 22 HTTP429 failures with no returned billing information.
- 1289 inference attempts total.
-Usage-reported charges: **$0.24488575444**.
-Unknown-error reservations conservatively charged: **$0.272415258**.
-Total conservative ledger accounting: **$0.517301071**, including nanodollar rounding; no outstanding reservations.

The full canonical experiment would cost approximately **$1.66 for 32640 evaluations**, or **$1.63 for 32064**, before retries, cache effects and price changes. Four counterbalanced conditions would be roughly4× the inference cost and define a different estimand; no such change is automatic. These estimates exclude human semantic review.

Use the new `configs/cloud-api-recommendation.json` as the proposed API configuration, with future budget default 0 and full-run authorization false. It pins only Cloudflare, retains T1/top_p1/top_logprobs20, and proposes concurrency 3 (tested; higher concurrency not validated). The existing experiment defaults and local implementation remain untouched; no local backend is required for this recommendation.

Next step: run a **separate Granite cloud24×20 pilot**, review whether its small-model behavior meaningfully follows the 24 constitutions, and test label/order effects on selected cases. The old Llama label/order findings do not automatically transfer, nor do they disappear. Decide canonical versus counterbalanced measurement before finalizing the design. Then resolve scenario approvals, freeze the new run manifest and explicit budget, and retain strict per-response validation/checkpoints. The full experiment remains unlaunched and unapproved.

For a future long run, repeat the 6 fixed canaries before starting and periodically during execution; stop on missing labels, wrong model/provider, probability differences>.001 or log-odds differences>.01. Do not silently fallback or merge a changed endpoint version. Observed exact repeatability over this bounded window is strong practical evidence, not a guarantee that a managed API will never change. This provides a simple cloud-only path forward without hardware ownership.

Primary sources: [recommended OpenRouter model](https://openrouter.ai/ibm-granite/granite-4.0-h-micro), [official Granite model card](https://huggingface.co/ibm-granite/granite-4.0-h-micro), plus archived OpenRouter models/endpoints and official Hugging Face model metadata retrieved2026-10-20. Provider rates/capabilities were checked live and then tested rather than assumed.
