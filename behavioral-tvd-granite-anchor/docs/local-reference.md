# Controlled local reference: implementation and deployment

Status: software implementation ready for hardware validation, NOT a validated 70B measurement backend. No full evaluation or scenario approval is authorized. The hosted pilot is unchanged; local inference is a new operational backend with its own identities, and no equality with hosted probabilities is assumed.

## Implementation

`constitution_distance.local` loads safetensors from an already downloaded local snapshot only (`local_files_only=True`, no remote code). The separate acquisition script requires immutable revisions and an explicit `--allow-70b-download` flag for the large model; it is never called by inference. No 70B weights were downloaded in this task.

The `lock` command requires snapshot directory names matching 40-character revision IDs, hashes all artifacts, and records both model and tokenizer revisions. Every execution verifies the hashes before loading. A lock proves the local artifacts have not changed; obtaining the snapshot from the official gated repository remains part of acquisition provenance. Model ID and architecture are checked for the 70B reference; quantized configurations, quantized runtime models, unexpected floating weight dtypes and CPU/disk offloading are rejected. The official revision observed via free repository metadata was `6f6073b423013f6a7d4d9f39144961bfbfbc386b`; weight access was not granted here (config GET401, no HF token). Treat it as the proposed revision until an authorized snapshot is downloaded and sealed.

Prompts use existing `core.messages` definitions. `data/local-validation/diagnostic19.json` contains exactly the 19 prior selected pairs; `block480.json` contains the same 24 constitutions and 20 pilot scenarios, for later reliability validation only. Each message was compared with the original completed pilot and regenerated definitions. `provenance.json` preserves source hashes. These validation inputs do not approve any scenario for the scientific full run.

Tokenizer processing uses the snapshot's own `apply_chat_template(..., add_generation_prompt=True)`. Rendered UTF-8 text, full template, message ordering, exact token IDs, token hashes and candidate IDs are retained. Template-produced IDs must equal encoding the rendered text without additional special tokens. For each actual prompt, appending ASCII0 or1 must preserve every prompt token and append exactly one distinct token whose decoded text is exactly that digit. IDs are verified, not hard-coded.

Model execution uses unquantized BF16 (or explicitly selected FP16), `model.eval()`, `torch.inference_mode()`, deterministic algorithms, TF32 disabled, eager attention by default, and no sampling or `generate()`. It takes logits at the final actual prompt position, including for right-padded mixed-length batches; explicit attention masks and position IDs are supplied. The reference does not truncate overlength inputs. Errors are errors, never invented probabilities.

The two raw logits and their FP32 difference are saved. The primary probability is stable sigmoid(logit1−logit0), at T=1. Full-vocabulary `torch.log_softmax` in FP32 gives raw label log probabilities and unconditional probabilities; their sum is also retained. An unconditional probability can numerically underflow for an extremely small true mass; raw finite logits/logs remain available and this is not missing-token imputation. Conditional and unconditional probabilities remain distinct.

## Integrity and reproducibility

Run IDs hash the model/tokenizer artifact lock, exact inputs, configuration, prompt hashes, runtime metadata and reference source-file hash. Runtime provenance includes Python/PyTorch/Transformers/Accelerate/tokenizers versions, CUDA/cuDNN, GPU names/capabilities/memory, dtype, attention, template, padding, deterministic flags and device placement. The initial multi-GPU implementation uses Accelerate **sequential layer sharding**, tensor-parallel size 1; this is explicitly recorded and is not vLLM tensor parallelism. EightGiB/GPU is reserved from weight placement by default for runtime headroom; no offload fallback.

SQLite WAL with synchronous FULL stores atomic completed records with content hashes and unique immutable slots. An exclusive process lock prevents concurrent writers in an output root. Prompt archives and per-process records are exclusive-create files. Ordinary resume with the same session skips completed forwards; it still reloads and verifies local artifacts. Interrupted/unperformed cells remain missing. A new planned session deliberately repeats measurements after process restart. Session IDs, real interpreter process identities, batch members, input hashes, loading/forward/total time, input/padded tokens, throughput, and per-GPU allocated/reserved peak memory are retained. If interrupted partway through a mixed batch, resume runs only missing cells and records the changed composition. Use uninterrupted new sessions when a strictly controlled composition comparison is required.

Changing attention/cache/batch/software/hardware creates a separate configuration-derived run. Within-configuration analysis aggregates repeated processes but does not mix other configurations. It reports missing planned sessions and fails the gate until planned measurements and independent processes exist. A seed is recorded, never treated as proof of determinism. Cache modes: `off` (baseline), `prefill` (allocates cache but no reuse), and `split` (batch 1 prefix forward then final-prompt-token forward reusing `past_key_values`). These are separate scientific execution conditions.

Provisional fixed gates: every selected pair's maximum probability range<=.001 AND log-odds range<=.01. Later complete blocks also require maximum change in pairwise normalized L1<=.005. These are engineering tolerances, not scientific accuracy claims. Analysis reports all failures, never adjusts thresholds. For every complete 24×20 block it reports summedL1 and normalizedL1 (sum/20). Partial blocks cannot pass the block gate. Outputs do not approve scenarios or launch another stage.

## Tests and current limits

Run offline tests with local dependencies installed:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The fixture integration command below constructs a tiny RANDOM Llama with BF16 weights and the official public SmolLM2 tokenizer; it exercises the real Transformers model/loader, process restarts, resume, padded batching, eager/SDPA, and cache reuse. It is explicitly not a pretrained model and not evidence about 70B numerical reliability. Generated fixture weights stay outside Git.

```bash
PYTHONPATH=src HF_HUB_OFFLINE=1 python scripts/test_local_integration.py \
  --tokenizer-snapshot /path/to/SmolLM2/snapshots/12fd25f77366fa6b3b4b768ec3050bf629380bac \
  --output /scratch/local-fixture-test-new
```

A public pretrained `HuggingFaceTB/SmolLM2-135M-Instruct` download was attempted at pinned revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`. Its tokenizer was available but weight redirects to `us.aws.cdn.hf.co` were blocked with proxy403. The user supplied the host to allow; at last observed policy readiness it was not yet effective. No bypass was attempted. Once enabled, download that small model with `scripts/download_local_model.py`, lock it, and run the benchmark with `--device cpu --software-test --repeats 2` on a small subset. The full official pretrained-small-model check remains distinct from the successful random-weight fixture checks.

## Hardware and feasibility

Current environment: no visible NVIDIA GPU/`nvidia-smi`, ~9.7GiBRAM and~30GiB free disk initially. It cannot download/store or run the 70B BF16 model. There is no70B numerical acceptance result. No rented resources, inference API calls or external compute spending were incurred.

BF16/FP16 weights need~140–142GB decimal (~131GiB) plus activations, logits and attention workspaces. Two80GB A100/H100 GPUs are the initial low-batch target; four80GB GPUs offer more headroom for mixed batches. An80GB single GPU is insufficient without changing precision/offloading, neither of which is silently permitted. Even two80GB GPUs may OOM for eager mixed batches; the code fails instead of changing precision or offloading. Reduce declared batch size in a new configuration, or provide more memory. A single141GB H200 is too tight to assume. Blackwell requires a separately validated newer software stack, so it is not the default deployment for these pinned packages.

Allow192–256GB hostRAM, ~250–350GB scratch for weights, environments, cache and results; more for duplicate model snapshots. The70B architecture has 80 layers, 8 KV heads and head dimension 128; BF16 KV cache is~.3125MiB/token/sequence (~1.25GiB at4096tokens) across layers, separate from weights/activations. Cache-off avoids retaining KV output, not all attention workspaces. Eager full-position logits and attention use additional memory; the default intentionally favors transparency over throughput.

Startup estimates:140GB transfer alone is~19minutes at1Gb/s or~2minutes at10Gb/s ideal sustained throughput. Allow~10–60+minutes for authentication, actual download speed and installation, then~2–15minutes for hashes/loading per fresh process depending storage and hostRAM. Each restart reloads weights. Current lock verification also verifies tokenizer snapshot contents; colocated model/tokenizer snapshots incur repeated file hashing. No throughput benchmark is available for 70B on these resources.

The19-pair benchmark performs570 forwards/session,1,140 across two processes, processing roughly a few million prompt tokens in total. At illustrative batch-one full-prompt latencies1–10seconds it takes~19–190minutes of forwards, plus startup. Actual eager layer-sharded execution can be slower; measure and stop/rebudget before further conditions. Indicative two-H100 advertised cost~$5.78–7.98/hour, twoA100~$3.58/hour; budget roughly$10–40+ for initial reference validation including loading, with substantial uncertainty, storage extra. No purchase is authorized. Four additional conditions and later480-cell blocks multiply work; benchmark reference first rather than reserving all jobs at once.

## Exact deployment commands (future authorized hardware only)

Use an approved research GPU node or separately authorized rental. Provision gated Meta model access outside Git. Commands below perform acquisition only when explicitly invoked by the investigator; they were NOT executed for 70B here. Keep one stable CUDA_VISIBLE_DEVICES ordering for all restart sessions.

```bash
python3.12 -m venv .venv-local
source .venv-local/bin/activate
python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
python -m pip install -e '.[local]'
python -m pip freeze > /scratch/reference-software-lock.txt
export HF_HOME=/scratch/hf
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export CUDA_VISIBLE_DEVICES=0,1

# Only after explicit authorization to download ~142GB and license/access setup:
local_snapshot=$(python scripts/download_local_model.py \
  --model meta-llama/Llama-3.3-70B-Instruct \
  --revision 6f6073b423013f6a7d4d9f39144961bfbfbc386b \
  --allow-70b-download)
python -m constitution_distance.local_cli lock \
  --snapshot "$local_snapshot" --model-id meta-llama/Llama-3.3-70B-Instruct \
  --revision 6f6073b423013f6a7d4d9f39144961bfbfbc386b \
  --out /scratch/llama70b-lock.json

# Safe default: dry-run only, no loading/inference.
bash scripts/local_70b_benchmark.sh /scratch/llama70b-lock.json /scratch/local-validation reference
# Later explicit benchmark invocation: two separate Python processes, 30 repeats each.
bash scripts/local_70b_benchmark.sh /scratch/llama70b-lock.json /scratch/local-validation reference --execute
```

The executable prints the configuration-derived run directory. Analyze it, replacing RUN_SHA with that printed directory name; use a new analysis filename each time because reports are immutable:

```bash
python -m constitution_distance.local_cli analyze \
  --run /scratch/local-validation/reference/RUN_SHA \
  --out /scratch/reference-analysis-1.json
```

Only after reviewing reference results, launch explicitly selected comparisons (not an automatic continuation):

```bash
bash scripts/local_70b_benchmark.sh /scratch/llama70b-lock.json /scratch/local-validation mixed --execute
bash scripts/local_70b_benchmark.sh /scratch/llama70b-lock.json /scratch/local-validation sdpa --execute
bash scripts/local_70b_benchmark.sh /scratch/llama70b-lock.json /scratch/local-validation prefill --execute
bash scripts/local_70b_benchmark.sh /scratch/llama70b-lock.json /scratch/local-validation split --execute
# Later, after acceptance/rebudgeting: 2 complete480-cell blocks per process,2 processes.
bash scripts/local_70b_benchmark.sh /scratch/llama70b-lock.json /scratch/local-validation block --execute
```

Ordinary rerun of the identical command resumes valid checkpoints without repeating completed forwards. To obtain additional deliberate repetitions, plan the session set/repeat count before the run; changing them yields a new run. The CLI is validation-only and refuses more than480 input cells. It cannot launch24×1360.

## vLLM preparation, deliberately separate

Reviewed current upstream `vllm/config/model.py`: `logprobs_mode` supports `raw_logits`, `raw_logprobs`, `processed_logits`, `processed_logprobs`; raw modes are before logits processors. These modes differ scientifically. Engine versions must actually support the requested mode; no fallback to processed/top-k scores. A complete vocabulary raw-vector export would permit exactly the same FP32 normalization as the reference. Merely seeing two top-logprob entries is not a substitute for this direct-logit reference.

`constitution_distance.vllm_validation` is an experimental export validator and reference-comparison gate, NOT an executed vLLM inference backend. It rejects wrong revisions/token IDs, truncated vectors, processed scores and missing runtime provenance. No engine runner is enabled until its extraction path is validated on the selected GPU/build. This is intentional: no untested optimizer can silently replace the working reference. Hardware work remains necessary to implement/verify the engine-specific raw-vector collection for an actual pinned release.

Official reproducibility guidance requires identical hardware/version and deterministic scheduling or batch-invariance controls; a seed is insufficient. `VLLM_BATCH_INVARIANT=1` is not evidence of success by itself. The inspected tested-model list includes Llama3.1/3.2, not this exact 3.3 70B hardware configuration. Pin a separate vLLM environment/container, record tensor parallelism/kernel/cache modes, export raw vectors for the identical archived token IDs, and compare each pair against the accepted Transformers reference (initial cross-backend tolerance .001 probability/.01 log-odds). Independently repeat within that backend and vary batch composition. If either gate fails, retain Transformers and report the discrepancy, never relax criteria automatically. The reference currently uses sequential layer sharding, so comparison with tensor-parallel vLLM also changes the numerical execution condition.

Sources inspected2026-10-20 (source content hashes archived in `results/local-reference/vllm-investigation.json`):

- https://github.com/vllm-project/vllm/blob/main/vllm/config/model.py
- https://docs.vllm.ai/en/stable/usage/reproducibility/
- https://docs.vllm.ai/en/stable/features/batch_invariance/
- https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct
- Pricing is indicative from the prior diagnostic report, not a live reservation or guaranteed quote.

Remaining decisions: authorize hardware/access and artifact acquisition; accept/adjust provisional thresholds explicitly; run70B reference validation; choose canonical versus counterbalanced prompt estimand; separately resolve scenario review; benchmark cost before approving any full experimental run. No local software result finalizes these decisions.

To compare separate completed attention/cache/batch configurations without merging them:

```bash
python -m constitution_distance.local_cli compare \
  --reference /scratch/local-validation/reference/REFERENCE_RUN_SHA \
  --candidate /scratch/local-validation/sdpa/SDPA_RUN_SHA \
  --out /scratch/reference-vs-sdpa-1.json
```

This comparison requires complete planned coverage, matching prompt tokens and artifact checksums; it reports changes in means and within-configuration ranges separately. Passing within-configuration reproducibility does not imply agreement between configurations.

## Recorded software validation results

All 42 automated tests passed with the local dependency set installed; no tensor tests were skipped. The final random-weight Llama integration completed 60 forwards across five configurations and two fresh processes/configuration. All five ordinary resumes performed zero forwards. Every within-configuration probability/log-odds range was zero for this fixture. Between eager and SDPA, the largest probability difference was~.000244134 and log-odds difference~.000976563; mixed batches and the two cache alternatives agreed with eager baseline in this fixture. This illustrates why between-configuration agreement must be checked separately even when each configuration repeats exactly. It says nothing about 70B error magnitudes.

The 480-cell input was dry-run only (1,920 planned evaluations for four blocks). Its distance machinery was verified with synthetic complete blocks in an offline test, including symmetry, diagonal, summed/mean relationship and the fixed change threshold. No real 70B block was evaluated. Detailed summaries, raw fixture evidence, artifact hashes, software versions and dry-run counts are versioned in `results/local-reference/`.
