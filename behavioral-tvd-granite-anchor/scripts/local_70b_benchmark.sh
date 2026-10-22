#!/usr/bin/env bash
# Run only on authorized hardware after weights are downloaded and locked.
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo 'Usage: bash scripts/local_70b_benchmark.sh LOCK_JSON OUTPUT [reference|mixed|sdpa|prefill|split|block] [--execute]' >&2
  exit 2
fi
local_lock=$1
local_output=$2
local_condition=${3:-reference}
local_mode=${4:---dry-run}
local_flags=()
local_inputs=data/local-validation/diagnostic19.json
local_repeats=30
case "$local_condition" in
 reference) ;;
 mixed) local_flags+=(--batch-size 4) ;;
 sdpa) local_flags+=(--attention sdpa) ;;
 prefill) local_flags+=(--cache prefill) ;;
 split) local_flags+=(--cache split) ;;
 block) local_inputs=data/local-validation/block480.json;local_repeats=2 ;;
 *) echo 'Unknown condition' >&2;exit 2 ;;
esac
if [[ "$local_mode" != '--execute' && "$local_mode" != '--dry-run' ]]; then echo 'Use --execute or --dry-run' >&2;exit 2;fi
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
for local_session in restart-1 restart-2; do
 local_extra=()
 if [[ "$local_mode" == '--dry-run' ]];then local_extra+=(--dry-run);fi
 python -m constitution_distance.local_cli benchmark --lock "$local_lock" --inputs "$local_inputs" --output "$local_output/$local_condition" --session "$local_session" --repeats "$local_repeats" "${local_flags[@]}" "${local_extra[@]}"
done
