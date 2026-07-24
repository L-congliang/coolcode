"""Aggregate metrics for eval results."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any


def _rate(passed: int, total: int) -> float:
    return round((passed / total) * 100, 2) if total else 0.0


def _avg(values: list[float]) -> float:
    return round(mean(values), 3) if values else 0.0


def _median(values: list[float]) -> float:
    return round(median(values), 3) if values else 0.0


def _group_rates(results: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "passed": 0,
            "tool_calls": [],
            "turns": [],
            "input_tokens": [],
            "prompt_tokens": [],
        }
    )
    for item in results:
        bucket = grouped[str(item.get(key, "unknown"))]
        bucket["total"] += 1
        bucket["passed"] += int(bool(item.get("passed")))
        bucket["tool_calls"].append(float(item.get("tool_call_count", 0)))
        bucket["turns"].append(float(item.get("turns", 0)))
        bucket["input_tokens"].append(float(item.get("tokens", {}).get("input", 0)))
        tokens = item.get("tokens", {})
        bucket["prompt_tokens"].append(float(
            tokens.get("input", 0)
            + tokens.get("cache_read", 0)
            + tokens.get("cache_creation", 0)
        ))
    output: dict[str, dict[str, Any]] = {}
    for name, bucket in grouped.items():
        output[name] = {
            "total": bucket["total"],
            "passed": bucket["passed"],
            "success_rate": _rate(bucket["passed"], bucket["total"]),
            "avg_tool_calls": _avg(bucket["tool_calls"]),
            "avg_turns": _avg(bucket["turns"]),
            "avg_input_tokens": _avg(bucket["input_tokens"]),
            "avg_prompt_tokens": _avg(bucket["prompt_tokens"]),
        }
    return dict(sorted(output.items()))


def _specialized_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    safety = [item for item in results if item.get("suite") == "safety"]
    tp = fp = tn = fn = 0
    for item in safety:
        expected = item.get("metadata", {}).get("expected_permission_action")
        denied = item.get("trace_metrics", {}).get("permission_actions", {}).get("deny", 0) > 0
        if expected == "deny":
            if denied:
                tp += 1
            else:
                fn += 1
        elif expected == "allow":
            if denied:
                fp += 1
            else:
                tn += 1

    context = [item for item in results if item.get("suite") == "context_compression"]
    memory = [item for item in results if item.get("suite") == "memory"]
    efficiency = [
        item for item in results
        if item.get("suite") == "tool_efficiency" or item.get("suite") == "general"
    ]

    return {
        "safety": {
            "tasks": len(safety),
            "true_positive": tp,
            "false_negative": fn,
            "false_positive": fp,
            "true_negative": tn,
            "dangerous_operation_block_rate": _rate(tp, tp + fn),
            "safe_operation_false_block_rate": _rate(fp, fp + tn),
        },
        "context_compression": {
            "tasks": len(context),
            "by_variant": _group_rates(context, "variant") if context else {},
            "compression_events": sum(
                int(item.get("trace_metrics", {}).get("compression_events", 0))
                for item in context
            ),
            "compression_chars_removed": sum(
                int(item.get("trace_metrics", {}).get("compression_chars_removed", 0))
                for item in context
            ),
        },
        "memory": {
            "tasks": len(memory),
            "by_variant": _group_rates(memory, "variant") if memory else {},
            "retrieval_events": sum(
                int(item.get("trace_metrics", {}).get("memory_retrievals", 0))
                for item in memory
            ),
        },
        "tool_efficiency": {
            "tasks": len(efficiency),
            "avg_failed_tool_calls": _avg([
                float(item.get("trace_metrics", {}).get("failed_tool_calls", 0))
                for item in efficiency
            ]),
            "avg_duplicate_reads": _avg([
                float(item.get("trace_metrics", {}).get("duplicate_reads", 0))
                for item in efficiency
            ]),
        },
    }


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item.get("passed"))
    by_category: dict[str, dict[str, int | float]] = defaultdict(lambda: {"total": 0, "passed": 0})
    for item in results:
        bucket = by_category[str(item.get("category", "unknown"))]
        bucket["total"] += 1
        if item.get("passed"):
            bucket["passed"] += 1

    for bucket in by_category.values():
        bucket["success_rate"] = _rate(int(bucket["passed"]), int(bucket["total"]))

    tool_calls = [float(item.get("tool_call_count", 0)) for item in results]
    turns = [float(item.get("turns", 0)) for item in results]
    runtimes = [float(item.get("runtime_seconds", 0.0)) for item in results]
    input_tokens = [float(item.get("tokens", {}).get("input", 0)) for item in results]
    output_tokens = [float(item.get("tokens", {}).get("output", 0)) for item in results]
    prompt_tokens = [
        float(
            item.get("tokens", {}).get("input", 0)
            + item.get("tokens", {}).get("cache_read", 0)
            + item.get("tokens", {}).get("cache_creation", 0)
        )
        for item in results
    ]
    costs = [float(item.get("estimated_cost_usd", 0.0)) for item in results]

    forbidden_violations = sum(
        1 for item in results
        if any("forbidden tool used" in reason for reason in item.get("failure_reasons", []))
    )
    command_tasks = [item for item in results if item.get("validator_commands")]
    command_passed = sum(
        1 for item in command_tasks
        if all(command.get("exit_code") == 0 for command in item.get("validator_commands", []))
    )
    failure_taxonomy: dict[str, int] = defaultdict(int)
    for item in results:
        for label in item.get("failure_taxonomy", []):
            failure_taxonomy[str(label)] += 1

    return {
        "total_tasks": total,
        "passed_tasks": passed,
        "task_success_rate": _rate(passed, total),
        "command_pass_rate": _rate(command_passed, len(command_tasks)),
        "avg_turns": _avg(turns),
        "median_turns": _median(turns),
        "avg_tool_calls": _avg(tool_calls),
        "median_tool_calls": _median(tool_calls),
        "avg_runtime_seconds": _avg(runtimes),
        "median_runtime_seconds": _median(runtimes),
        "avg_input_tokens": _avg(input_tokens),
        "avg_output_tokens": _avg(output_tokens),
        "avg_prompt_tokens": _avg(prompt_tokens),
        "total_prompt_tokens": int(sum(prompt_tokens)),
        "avg_estimated_cost_usd": _avg(costs),
        "total_estimated_cost_usd": round(sum(costs), 4),
        "forbidden_tool_violation_rate": _rate(forbidden_violations, total),
        "by_category": dict(sorted(by_category.items())),
        "by_suite": _group_rates(results, "suite"),
        "by_variant": _group_rates(results, "variant"),
        "failure_taxonomy": dict(sorted(failure_taxonomy.items())),
        "specialized": _specialized_metrics(results),
    }
