"""Overlay task retests onto a base run without mutating original artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .metrics import aggregate_results
from .report import write_json, write_summary_md, write_tasks_jsonl


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_tasks(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Overlay eval retests onto a base run.")
    parser.add_argument("base", type=Path)
    parser.add_argument("--overlay", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_summary = read_json(args.base / "summary.json")
    base_results = read_tasks(args.base / "tasks.jsonl")
    order = [item["task_id"] for item in base_results]
    merged = {item["task_id"]: item for item in base_results}
    replacements: list[dict] = []

    for overlay in args.overlay:
        for item in read_tasks(overlay / "tasks.jsonl"):
            task_id = item["task_id"]
            if task_id not in merged:
                continue
            merged[task_id] = item
            replacements.append({"task_id": task_id, "source": str(overlay)})

    results = [merged[task_id] for task_id in order]
    metrics = aggregate_results(results)
    args.output.mkdir(parents=True, exist_ok=True)
    run_id = args.output.name
    payload = {
        "run_id": run_id,
        "dry_run": False,
        "provider": base_summary.get("provider"),
        "model": base_summary.get("model"),
        "metrics": metrics,
        "tasks": order,
        "consolidated": True,
    }
    write_json(args.output / "summary.json", payload)
    write_tasks_jsonl(args.output / "tasks.jsonl", results)
    write_json(
        args.output / "provenance.json",
        {
            "base": str(args.base),
            "overlays": [str(path) for path in args.overlay],
            "replacements": replacements,
        },
    )
    write_summary_md(
        args.output / "summary.md",
        run_id=run_id,
        dry_run=False,
        provider=str(base_summary.get("provider", "unknown")),
        model=str(base_summary.get("model", "unknown")),
        metrics=metrics,
        results=results,
    )
    print(f"Consolidated {len(results)} tasks with {len(replacements)} replacements.")
    print(f"Summary: {args.output / 'summary.md'}")


if __name__ == "__main__":
    main()
