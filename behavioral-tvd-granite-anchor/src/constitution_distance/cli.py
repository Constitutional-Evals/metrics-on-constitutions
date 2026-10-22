from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

from .api import API
from .core import digest, unique_dilemmas
from .runner import run, write_json, export_existing
from .prepare import prepare

def fetch(args):
    output = Path(args.output)
    if output.exists() or output.with_suffix(".source.json").exists():
        raise ValueError("Output or provenance file already exists; choose a new output path")
    api = API("https://datasets-server.huggingface.co")
    # Stage the complete download before replacing the output. Dataset indices are stable
    # within this download; the saved file hash pins the actual evaluation input.
    rows, source_rows, offset, total, column = [], [], 0, None, args.text_column
    while total is None or offset < total:
        response = api.request("/rows?" + urlencode({"dataset": args.dataset,
            "config": args.config, "split": args.split, "offset": offset, "length": 100}))
        if total is None:
            total = response["num_rows_total"]
            columns = [f["name"] for f in response["features"]]
            if not column:
                candidates = [c for c in columns if c.lower() in {"scenario", "dilemma", "question", "text"}]
                if {"dilemma_idx", "dilemma_situation", "action_type"} <= set(columns):
                    candidates = ["dilemma_situation"]
                if len(candidates) != 1:
                    raise ValueError(f"Choose --text-column explicitly from: {columns}")
                column = candidates[0]
            if column not in columns:
                raise ValueError(f"Missing column {column!r}; available: {columns}")
        elif response["num_rows_total"] != total:
            raise ValueError("Dataset size changed during download; retry into a new file")
        batch = response["rows"]
        if not batch and offset < total:
            raise ValueError("Dataset server returned an incomplete page")
        for item in batch:
            if item["row_idx"] != offset:
                raise ValueError("Dataset row order changed or a page was incomplete")
            if set(item.get("truncated_cells", [])) & {column, "action", "action_type", "dilemma_idx"}:
                raise ValueError("Scenario text is truncated by the dataset server")
            text = item["row"].get(column)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Non-text or empty scenario at row {offset}")
            rows.append({"id": str(offset), "text": text})
            if column == "dilemma_situation":
                source_rows.append({k: item["row"][k] for k in
                    ("dilemma_idx", "dilemma_situation", "action_type", "action", "topic", "topic_group")})
            offset += 1
        print(f"Downloaded {offset}/{total}", file=sys.stderr)
    if not rows:
        raise ValueError("Dataset contains no scenarios")
    if column == "dilemma_situation":
        rows = unique_dilemmas(source_rows)
        if (args.dataset, args.config, args.split) == (
                "kellycyy/daily_dilemmas", "Dilemmas_with_values_aggregated", "test"):
            if total != 2720 or len(rows) != 1360:
                raise ValueError("Expected 2720 action rows and 1360 unique dilemmas")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    temp.replace(output)
    write_json(output.with_suffix(".source.json"), {
        "dataset": args.dataset, "config": args.config, "split": args.split,
        "text_column": column, "source_rows": total, "rows": len(rows),
        "deduplication_key": "dilemma_idx" if source_rows else None,
        "content_sha256": digest(rows),
        "downloaded_at": datetime.now(timezone.utc).isoformat()})


def parser():
    p = argparse.ArgumentParser(description="Budgeted constitution action-probability experiments")
    subs = p.add_subparsers(dest="command", required=True)
    f = subs.add_parser("fetch", help="Download action pairs and exclude all outcome/value annotations")
    f.add_argument("--dataset", default="kellycyy/daily_dilemmas")
    f.add_argument("--config", default="Dilemmas_with_values_aggregated")
    f.add_argument("--split", default="test")
    f.add_argument("--text-column")
    f.add_argument("--output", default="data/scenarios-v2.jsonl")
    f.set_defaults(function=fetch)
    s = subs.add_parser("prepare", help="Audit action pairs and select a seeded topic-stratified pilot")
    s.add_argument("--scenarios", default="data/scenarios-v2.jsonl")
    s.add_argument("--seed", type=int, default=20261020)
    s.add_argument("--size", type=int, default=20)
    s.add_argument("--output", default="data/pilot-v2")
    s.set_defaults(function=prepare)
    e = subs.add_parser("export", help="Rebuild matrices and missing-data reports offline; makes no API calls")
    e.add_argument("--output", required=True, help="Existing run directory with its manifest and ledger")
    e.set_defaults(function=export_existing)
    r = subs.add_parser("run", help="Run/resume with a durable shared monetary ledger")
    r.add_argument("--model", default="meta-llama/llama-3.3-70b-instruct")
    r.add_argument("--provider", default="parasail/fp8")
    r.add_argument("--scenarios", default="data/scenarios-v2.jsonl")
    r.add_argument("--constitutions", default="data/constitutions")
    r.add_argument("--constitution-ids", nargs="+")
    r.add_argument("--output", default="runs/default-v2")
    r.add_argument("--limit", type=int)
    r.add_argument("--concurrency", type=int, default=4)
    r.add_argument("--attempts", type=int, default=3, help="Max attempts per evaluation, including retries")
    r.add_argument("--top-logprobs", type=int, default=20)
    r.add_argument("--metric", choices=["p1", "p1_conditional"], default="p1_conditional")
    r.add_argument("--budget-usd", type=float, default=0, help="Explicit total ledger spending ceiling; default zero")
    r.add_argument("--ledger", default="runs/budget.sqlite", help="Share this ledger across all phases charged to one budget")
    r.add_argument("--input-price", type=float, default=.22, help="Maximum USD per million input tokens")
    r.add_argument("--output-price", type=float, default=.50, help="Maximum USD per million output tokens")
    r.add_argument("--replicates", type=int, default=1, help="Intentional identical repeats, kept outside the primary matrix")
    r.add_argument("--phase", default="main", help="Named experimental phase, included in run identifier")
    r.add_argument("--retry-missing", action="store_true", help="Explicitly retry previously invalid/failed pairs; never completed or uncertain pairs")
    r.add_argument("--max-requests", type=int, default=None, help="Hard per-run dispatch cap including retries")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(function=run)
    return p


def main():
    args = parser().parse_args()
    try:
        args.function(args)
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
