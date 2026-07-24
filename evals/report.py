"""Markdown and JSON report writers for eval runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def write_tasks_jsonl(path: Path, results: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for item in results:
            fh.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")


def write_summary_md(
    path: Path,
    *,
    run_id: str,
    dry_run: bool,
    provider: str,
    model: str,
    metrics: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Eval Summary",
        "",
        f"- Run ID: {run_id}",
        f"- Mode: {'dry-run oracle' if dry_run else 'real API'}",
        f"- Provider: {provider}",
        f"- Model: {model}",
        f"- Total tasks: {metrics['total_tasks']}",
        f"- Passed: {metrics['passed_tasks']}",
        f"- Success rate: {metrics['task_success_rate']}%",
        f"- Command pass rate: {metrics['command_pass_rate']}%",
        f"- Avg turns: {metrics['avg_turns']}",
        f"- Avg tool calls: {metrics['avg_tool_calls']}",
        f"- Avg runtime: {metrics['avg_runtime_seconds']}s",
        f"- Avg prompt tokens (including cache): {metrics.get('avg_prompt_tokens', 0)}",
        f"- Total prompt tokens (including cache): {metrics.get('total_prompt_tokens', 0)}",
        f"- Total estimated cost: ${metrics['total_estimated_cost_usd']}",
        "",
        "## By Category",
        "",
        "| Category | Passed | Total | Rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, bucket in metrics["by_category"].items():
        lines.append(
            f"| {category} | {bucket['passed']} | {bucket['total']} | {bucket['success_rate']}% |"
        )

    lines.extend([
        "",
        "## By Suite",
        "",
        "| Suite | Passed | Total | Rate | Avg Tools | Avg Turns |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for suite, bucket in metrics.get("by_suite", {}).items():
        lines.append(
            f"| {suite} | {bucket['passed']} | {bucket['total']} | "
            f"{bucket['success_rate']}% | {bucket['avg_tool_calls']} | {bucket['avg_turns']} |"
        )

    specialized = metrics.get("specialized", {})
    safety = specialized.get("safety", {})
    context = specialized.get("context_compression", {})
    memory = specialized.get("memory", {})
    efficiency = specialized.get("tool_efficiency", {})
    lines.extend([
        "",
        "## Specialized Metrics",
        "",
        f"- Safety block rate: {safety.get('dangerous_operation_block_rate', 0.0)}%",
        f"- Safety false block rate: {safety.get('safe_operation_false_block_rate', 0.0)}%",
        f"- Compression events: {context.get('compression_events', 0)}",
        f"- Compression chars removed: {context.get('compression_chars_removed', 0)}",
        f"- Memory retrieval events: {memory.get('retrieval_events', 0)}",
        f"- Avg failed tool calls: {efficiency.get('avg_failed_tool_calls', 0.0)}",
        f"- Avg duplicate reads: {efficiency.get('avg_duplicate_reads', 0.0)}",
    ])

    failures = [item for item in results if not item.get("passed")]
    lines.extend(["", "## Failures", ""])
    if not failures:
        lines.append("No failures.")
    else:
        lines.extend(["| Task | Category | Reason |", "| --- | --- | --- |"])
        for item in failures:
            reason = "; ".join(item.get("failure_reasons", [])) or "unknown"
            lines.append(f"| {item['task_id']} | {item['category']} | {reason} |")

    lines.extend(["", "## Task Results", ""])
    lines.extend(["| Task | Category | Passed | Tools | Runtime |", "| --- | --- | ---: | ---: | ---: |"])
    for item in results:
        lines.append(
            f"| {item['task_id']} | {item['category']} | {str(bool(item['passed'])).lower()} | "
            f"{item.get('tool_call_count', 0)} | {item.get('runtime_seconds', 0.0)}s |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
