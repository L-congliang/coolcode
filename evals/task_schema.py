"""Task schema and loading helpers for repo-level agent evaluations."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass
class AgentConfig:
    permission_mode: str = "acceptEdits"
    max_turns: int = 8
    max_cost_usd: float | None = 0.2
    model: str | None = None
    thinking: bool = False
    compression_mode: str = "default"
    effective_context_window: int | None = None
    memory_enabled: bool = True


@dataclass
class SuccessCriteria:
    commands: list[str] = field(default_factory=list)
    file_contains: dict[str, list[str]] = field(default_factory=dict)
    file_not_contains: dict[str, list[str]] = field(default_factory=dict)
    expected_modified: list[str] = field(default_factory=list)
    forbidden_modified: list[str] = field(default_factory=list)


@dataclass
class TraceExpectations:
    required_tools: list[str] = field(default_factory=list)
    required_tool_groups: list[list[str]] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    max_tool_calls: int | None = None
    max_turns: int | None = None
    required_permission_actions: list[str] = field(default_factory=list)
    min_permission_denials: int = 0
    min_compression_events: int = 0
    min_memory_retrievals: int = 0
    forbidden_read_paths: list[str] = field(default_factory=list)


@dataclass
class Task:
    id: str
    category: str
    fixture: Path
    prompt: str
    suite: str = "general"
    variant: str = "default"
    episode_id: str | None = None
    risk_tags: list[str] = field(default_factory=list)
    prelude_prompts: list[str] = field(default_factory=list)
    reset_agent_between_prompts: bool = False
    memory_entries: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    agent: AgentConfig = field(default_factory=AgentConfig)
    success: SuccessCriteria = field(default_factory=SuccessCriteria)
    trace_expectations: TraceExpectations = field(default_factory=TraceExpectations)
    oracle: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None


def _load_raw_task(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                f"{path} is YAML, but PyYAML is not installed. Use JSON tasks or install PyYAML."
            ) from exc
        return yaml.safe_load(text)
    raise ValueError(f"Unsupported task file type: {path}")


def _list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(f"Expected list[str], got {type(value).__name__}")
    return [str(item) for item in value]


def _map_to_string_lists(value: Any) -> dict[str, list[str]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"Expected mapping, got {type(value).__name__}")
    return {str(k): _list_of_strings(v) for k, v in value.items()}


def task_from_file(path: Path, *, eval_root: Path) -> Task:
    raw = _load_raw_task(path)
    agent_raw = raw.get("agent") or {}
    success_raw = raw.get("success") or {}
    trace_raw = raw.get("trace_expectations") or {}

    fixture = Path(str(raw["fixture"]))
    if not fixture.is_absolute():
        fixture = (eval_root / fixture).resolve()

    agent = AgentConfig(
        permission_mode=str(agent_raw.get("permission_mode", "acceptEdits")),
        max_turns=int(agent_raw.get("max_turns", 8)),
        max_cost_usd=agent_raw.get("max_cost_usd", 0.2),
        model=agent_raw.get("model"),
        thinking=bool(agent_raw.get("thinking", False)),
        compression_mode=str(agent_raw.get("compression_mode", "default")),
        effective_context_window=(
            int(agent_raw["effective_context_window"])
            if agent_raw.get("effective_context_window") is not None else None
        ),
        memory_enabled=bool(agent_raw.get("memory_enabled", True)),
    )
    success = SuccessCriteria(
        commands=_list_of_strings(success_raw.get("commands")),
        file_contains=_map_to_string_lists(success_raw.get("file_contains")),
        file_not_contains=_map_to_string_lists(success_raw.get("file_not_contains")),
        expected_modified=_list_of_strings(success_raw.get("expected_modified")),
        forbidden_modified=_list_of_strings(success_raw.get("forbidden_modified")),
    )
    trace = TraceExpectations(
        required_tools=_list_of_strings(trace_raw.get("required_tools")),
        required_tool_groups=[
            _list_of_strings(group) for group in (trace_raw.get("required_tool_groups") or [])
        ],
        forbidden_tools=_list_of_strings(trace_raw.get("forbidden_tools")),
        max_tool_calls=trace_raw.get("max_tool_calls"),
        max_turns=trace_raw.get("max_turns"),
        required_permission_actions=_list_of_strings(
            trace_raw.get("required_permission_actions")
        ),
        min_permission_denials=int(trace_raw.get("min_permission_denials", 0)),
        min_compression_events=int(trace_raw.get("min_compression_events", 0)),
        min_memory_retrievals=int(trace_raw.get("min_memory_retrievals", 0)),
        forbidden_read_paths=_list_of_strings(trace_raw.get("forbidden_read_paths")),
    )
    return Task(
        id=str(raw["id"]),
        category=str(raw["category"]),
        fixture=fixture,
        prompt=str(raw["prompt"]),
        suite=str(raw.get("suite", "general")),
        variant=str(raw.get("variant", "default")),
        episode_id=(str(raw["episode_id"]) if raw.get("episode_id") is not None else None),
        risk_tags=_list_of_strings(raw.get("risk_tags")),
        prelude_prompts=_list_of_strings(raw.get("prelude_prompts")),
        reset_agent_between_prompts=bool(raw.get("reset_agent_between_prompts", False)),
        memory_entries=list(raw.get("memory_entries") or []),
        metadata=dict(raw.get("metadata") or {}),
        agent=agent,
        success=success,
        trace_expectations=trace,
        oracle=raw.get("oracle") or {},
        source_path=path,
    )


def load_tasks(tasks_dir: Path, *, eval_root: Path) -> list[Task]:
    files = sorted(
        path for path in tasks_dir.iterdir()
        if path.suffix.lower() in {".json", ".yaml", ".yml"}
    )
    return [task_from_file(path, eval_root=eval_root) for path in files]
