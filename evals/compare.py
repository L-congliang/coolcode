"""Compare two eval result runs and print a Markdown delta report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two CoolCode eval runs.")
    parser.add_argument("baseline", type=Path, help="Baseline run directory or summary.json")
    parser.add_argument("candidate", type=Path, help="Candidate run directory or summary.json")
    parser.add_argument("--output", type=Path, default=None, help="Optional Markdown output path")
    return parser.parse_args()


def resolve_summary(path: Path) -> Path:
    if path.is_dir():
        path = path / "summary.json"
    if not path.exists():
        raise SystemExit(f"summary not found: {path}")
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_tasks(summary_path: Path) -> dict[str, dict[str, Any]]:
    tasks_path = summary_path.parent / "tasks.jsonl"
    if not tasks_path.exists():
        return {}
    tasks: dict[str, dict[str, Any]] = {}
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        tasks[str(item["task_id"])] = item
    return tasks


def fmt_delta(value: float, *, prefix: str = "", suffix: str = "") -> str:
    rounded = round(value, 3)
    if rounded > 0:
        return f"+{prefix}{rounded}{suffix}"
    if rounded < 0:
        return f"-{prefix}{abs(rounded)}{suffix}"
    return f"{prefix}{rounded}{suffix}"


def format_value(value: float, *, prefix: str = "", suffix: str = "") -> str:
    return f"{prefix}{value}{suffix}"


def metric_row(
    label: str,
    key: str,
    base: dict[str, Any],
    cand: dict[str, Any],
    suffix: str = "",
    prefix: str = "",
) -> str:
    base_value = float(base.get(key, 0))
    cand_value = float(cand.get(key, 0))
    return (
        f"| {label} | {format_value(base_value, prefix=prefix, suffix=suffix)} | "
        f"{format_value(cand_value, prefix=prefix, suffix=suffix)} | "
        f"{fmt_delta(cand_value - base_value, prefix=prefix, suffix=suffix)} |"
    )


def category_rows(base: dict[str, Any], cand: dict[str, Any]) -> list[str]:
    rows = [
        "",
        "## Category Deltas",
        "",
        "| Category | Baseline | Candidate | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    base_categories = base.get("by_category", {})
    cand_categories = cand.get("by_category", {})
    for category in sorted(set(base_categories) | set(cand_categories)):
        base_rate = float(base_categories.get(category, {}).get("success_rate", 0))
        cand_rate = float(cand_categories.get(category, {}).get("success_rate", 0))
        rows.append(f"| {category} | {base_rate}% | {cand_rate}% | {fmt_delta(cand_rate - base_rate, suffix='%')} |")
    return rows


def task_rows(base_tasks: dict[str, dict[str, Any]], cand_tasks: dict[str, dict[str, Any]]) -> list[str]:
    rows = [
        "",
        "## Task Outcome Changes",
        "",
        "| Task | Baseline | Candidate | Notes |",
        "| --- | ---: | ---: | --- |",
    ]
    all_ids = sorted(set(base_tasks) | set(cand_tasks))
    if not all_ids:
        rows.append("| n/a | n/a | n/a | tasks.jsonl missing |")
        return rows

    for task_id in all_ids:
        base = base_tasks.get(task_id)
        cand = cand_tasks.get(task_id)
        base_passed = "missing" if base is None else str(bool(base.get("passed"))).lower()
        cand_passed = "missing" if cand is None else str(bool(cand.get("passed"))).lower()
        notes: list[str] = []
        if base and cand:
            tool_delta = int(cand.get("tool_call_count", 0)) - int(base.get("tool_call_count", 0))
            runtime_delta = float(cand.get("runtime_seconds", 0)) - float(base.get("runtime_seconds", 0))
            notes.append(f"tools {fmt_delta(tool_delta)}")
            notes.append(f"runtime {fmt_delta(runtime_delta, suffix='s')}")
            if base.get("passed") and not cand.get("passed"):
                notes.append("regressed")
            elif not base.get("passed") and cand.get("passed"):
                notes.append("fixed")
        rows.append(f"| {task_id} | {base_passed} | {cand_passed} | {', '.join(notes)} |")
    return rows


def build_report(baseline_path: Path, candidate_path: Path) -> str:
    baseline_summary = load_json(baseline_path)
    candidate_summary = load_json(candidate_path)
    base_metrics = baseline_summary["metrics"]
    cand_metrics = candidate_summary["metrics"]

    lines = [
        "# Eval Comparison",
        "",
        f"- Baseline: {baseline_summary.get('run_id', baseline_path.parent.name)}",
        f"- Candidate: {candidate_summary.get('run_id', candidate_path.parent.name)}",
        f"- Baseline model: {baseline_summary.get('model', 'unknown')}",
        f"- Candidate model: {candidate_summary.get('model', 'unknown')}",
        "",
        "## Overall Deltas",
        "",
        "| Metric | Baseline | Candidate | Delta |",
        "| --- | ---: | ---: | ---: |",
        metric_row("Success rate", "task_success_rate", base_metrics, cand_metrics, "%"),
        metric_row("Passed tasks", "passed_tasks", base_metrics, cand_metrics),
        metric_row("Avg turns", "avg_turns", base_metrics, cand_metrics),
        metric_row("Avg tool calls", "avg_tool_calls", base_metrics, cand_metrics),
        metric_row("Avg runtime", "avg_runtime_seconds", base_metrics, cand_metrics, "s"),
        metric_row("Avg estimated cost", "avg_estimated_cost_usd", base_metrics, cand_metrics, prefix="$"),
        metric_row("Forbidden tool violation rate", "forbidden_tool_violation_rate", base_metrics, cand_metrics, "%"),
    ]
    lines.extend(category_rows(base_metrics, cand_metrics))
    lines.extend(task_rows(load_tasks(baseline_path), load_tasks(candidate_path)))
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    baseline_path = resolve_summary(args.baseline)
    candidate_path = resolve_summary(args.candidate)
    report = build_report(baseline_path, candidate_path)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
