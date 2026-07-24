"""Run task-level evaluations against the CoolCode agent."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import datetime
import difflib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, TYPE_CHECKING

from .metrics import aggregate_results
from .report import write_json, write_summary_md, write_tasks_jsonl
from .task_schema import Task, load_tasks
from .trace import TraceRecorder, duration_ms

if TYPE_CHECKING:
    from coolcode.agent import Agent


EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parent
DEFAULT_TASKS_DIR = EVAL_ROOT / "tasks"
DEFAULT_RESULTS_DIR = EVAL_ROOT / "results"

IGNORED_NAMES = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    ".coolcode-memory",
    ".coolcode-skills",
}
IGNORED_FILES = {".coolcode-session.json", ".coolcode-mcp.json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CoolCode task evals.")
    parser.add_argument("--tasks", default="all", help="'all', a comma list, or one task id")
    parser.add_argument("--task", action="append", default=[], help="Task id to run; may be repeated")
    parser.add_argument("--category", default=None, help="Only run this category")
    parser.add_argument("--suite", default=None, help="Only run this evaluation suite")
    parser.add_argument("--variant", default=None, help="Only run this experiment variant")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of selected tasks")
    parser.add_argument("--model", default=None, help="Override model")
    parser.add_argument("--api-base", default=None, help="OpenAI-compatible API base URL")
    parser.add_argument("--permission-mode", default=None, help="Override task permission mode")
    parser.add_argument("--max-turns", type=int, default=None, help="Override task max turns")
    parser.add_argument("--max-cost", type=float, default=None, help="Override task max cost")
    parser.add_argument("--output-name", default=None, help="Suffix for the result run directory")
    parser.add_argument("--tasks-dir", type=Path, default=DEFAULT_TASKS_DIR)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic oracle edits; no API call")
    parser.add_argument("--keep-workspaces", action="store_true", help="Keep copied workspaces in results")
    parser.add_argument("--validation-timeout", type=int, default=30, help="Validator timeout in seconds")
    return parser.parse_args()


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_api(args: argparse.Namespace, *, dry_run: bool) -> dict[str, Any]:
    model = args.model or os.environ.get("COOLCODE_MODEL", "claude-opus-4-6")
    api_base = args.api_base
    api_key = None
    provider = "anthropic"
    use_openai = False

    if os.environ.get("OPENAI_API_KEY") and (api_base or os.environ.get("OPENAI_BASE_URL")):
        api_key = os.environ["OPENAI_API_KEY"]
        api_base = api_base or os.environ.get("OPENAI_BASE_URL")
        provider = "openai-compatible"
        use_openai = True
    elif os.environ.get("ANTHROPIC_API_KEY"):
        api_key = os.environ["ANTHROPIC_API_KEY"]
        api_base = api_base or os.environ.get("ANTHROPIC_BASE_URL")
        provider = "anthropic"
        use_openai = False
    elif os.environ.get("OPENAI_API_KEY"):
        api_key = os.environ["OPENAI_API_KEY"]
        api_base = api_base or os.environ.get("OPENAI_BASE_URL")
        provider = "openai-compatible"
        use_openai = True

    if not dry_run and not api_key:
        raise SystemExit(
            "No API key found. Set ANTHROPIC_API_KEY, or OPENAI_API_KEY plus OPENAI_BASE_URL, "
            "or run with --dry-run."
        )

    return {
        "provider": provider if not dry_run else "oracle",
        "model": model,
        "api_key": api_key,
        "api_base": api_base,
        "use_openai": use_openai,
    }


def make_run_id(output_name: str | None) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    suffix = f"_{output_name}" if output_name else ""
    return timestamp + suffix


def select_tasks(tasks: list[Task], args: argparse.Namespace) -> list[Task]:
    selected_ids: set[str] = set(args.task)
    if args.tasks and args.tasks != "all":
        selected_ids.update(part.strip() for part in args.tasks.split(",") if part.strip())

    selected = tasks
    if selected_ids:
        selected = [task for task in selected if task.id in selected_ids]
    if args.category:
        selected = [task for task in selected if task.category == args.category]
    if args.suite:
        selected = [task for task in selected if task.suite == args.suite]
    if args.variant:
        selected = [task for task in selected if task.variant == args.variant]
    if args.limit is not None:
        selected = selected[: args.limit]
    if not selected:
        raise SystemExit("No tasks selected.")
    return selected


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.name in IGNORED_FILES or path.suffix == ".pyc"


def collect_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_dir() or should_ignore(path.relative_to(root)):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            files[rel] = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            files[rel] = "<binary or unreadable>"
    return files


def make_diff(before: dict[str, str], after: dict[str, str]) -> tuple[str, list[str]]:
    changed: list[str] = []
    chunks: list[str] = []
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel)
        new = after.get(rel)
        if old == new:
            continue
        changed.append(rel)
        old_lines = [] if old is None else old.splitlines()
        new_lines = [] if new is None else new.splitlines()
        chunks.extend(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                lineterm="",
            )
        )
        chunks.append("\n")
    return "\n".join(chunks), changed


def run_validator_command(command: str, cwd: Path, timeout: int) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_ms": duration_ms(start),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"Timed out after {timeout}s",
            "duration_ms": duration_ms(start),
        }


def apply_oracle(task: Task, workspace: Path, recorder: TraceRecorder) -> str:
    for replacement in task.oracle.get("file_replacements", []):
        rel = replacement["file_path"]
        path = workspace / rel
        recorder.record("tool_call", tool="read_file", input={"file_path": rel})
        before = path.read_text(encoding="utf-8")
        recorder.record("tool_result", tool="read_file", ok=True, chars=len(before), duration_ms=0)

        old = replacement["old"]
        new = replacement["new"]
        if old not in before:
            raise RuntimeError(f"Oracle replacement did not match {rel}")
        recorder.record("tool_call", tool="edit_file", input={"file_path": rel})
        path.write_text(before.replace(old, new, 1), encoding="utf-8")
        recorder.record("tool_result", tool="edit_file", ok=True, chars=len(new), duration_ms=0)

    for file_write in task.oracle.get("write_files", []):
        rel = file_write["file_path"]
        recorder.record("tool_call", tool="write_file", input={"file_path": rel})
        (workspace / rel).parent.mkdir(parents=True, exist_ok=True)
        (workspace / rel).write_text(file_write["content"], encoding="utf-8")
        recorder.record("tool_result", tool="write_file", ok=True, chars=len(file_write["content"]), duration_ms=0)

    if task.success.commands:
        command = task.success.commands[0]
        recorder.record("tool_call", tool="run_shell", input={"command": command})
        result = run_validator_command(command, workspace, timeout=30)
        recorder.record(
            "tool_result",
            tool="run_shell",
            ok=result["exit_code"] == 0,
            chars=len(result["stdout"]) + len(result["stderr"]),
            duration_ms=result["duration_ms"],
        )

    return "Dry-run oracle applied the expected fix."


def validate_task(
    task: Task,
    workspace: Path,
    recorder: TraceRecorder,
    changed_files: list[str],
    validator_commands: list[dict[str, Any]],
    turns: int,
    dry_run: bool = False,
) -> list[str]:
    failures: list[str] = []

    for command in validator_commands:
        if command["exit_code"] != 0:
            failures.append(f"validator failed: {command['command']} exited {command['exit_code']}")

    for rel, needles in task.success.file_contains.items():
        path = workspace / rel
        if not path.exists():
            failures.append(f"missing file for contains check: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in needles:
            if needle not in text:
                failures.append(f"{rel} does not contain {needle!r}")

    for rel, needles in task.success.file_not_contains.items():
        path = workspace / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in needles:
            if needle in text:
                failures.append(f"{rel} still contains forbidden text {needle!r}")

    changed = set(changed_files)
    for rel in task.success.expected_modified:
        if rel not in changed:
            failures.append(f"expected file was not modified: {rel}")
    for rel in task.success.forbidden_modified:
        if rel in changed:
            failures.append(f"forbidden file was modified: {rel}")

    counts = recorder.tool_counts
    for tool in task.trace_expectations.required_tools:
        if counts.get(tool, 0) == 0:
            failures.append(f"required tool not used: {tool}")
    for group in task.trace_expectations.required_tool_groups:
        if group and not any(counts.get(tool, 0) for tool in group):
            failures.append(f"required tool group not used: {' or '.join(group)}")
    for tool in task.trace_expectations.forbidden_tools:
        if counts.get(tool, 0):
            failures.append(f"forbidden tool used: {tool}")
    if task.trace_expectations.max_tool_calls is not None:
        total_tool_calls = len(recorder.tool_calls)
        if total_tool_calls > task.trace_expectations.max_tool_calls:
            failures.append(
                f"too many tool calls: {total_tool_calls} > {task.trace_expectations.max_tool_calls}"
            )
    if task.trace_expectations.max_turns is not None and turns > task.trace_expectations.max_turns:
        failures.append(f"too many turns: {turns} > {task.trace_expectations.max_turns}")

    if not dry_run:
        permission_events = [
            event for event in recorder.events
            if event.get("event") == "permission_decision"
        ]
        permission_actions = [str(event.get("action", "")) for event in permission_events]
        for action in task.trace_expectations.required_permission_actions:
            if action not in permission_actions:
                failures.append(f"required permission action not observed: {action}")
        denials = sum(1 for action in permission_actions if action == "deny")
        if denials < task.trace_expectations.min_permission_denials:
            failures.append(
                f"too few permission denials: {denials} < "
                f"{task.trace_expectations.min_permission_denials}"
            )

        compression_events = [
            event for event in recorder.events
            if event.get("event") == "compression"
        ]
        if len(compression_events) < task.trace_expectations.min_compression_events:
            failures.append(
                f"too few compression events: {len(compression_events)} < "
                f"{task.trace_expectations.min_compression_events}"
            )

        memory_events = [
            event for event in recorder.events
            if event.get("event") == "memory_retrieve"
        ]
        if len(memory_events) < task.trace_expectations.min_memory_retrievals:
            failures.append(
                f"too few memory retrievals: {len(memory_events)} < "
                f"{task.trace_expectations.min_memory_retrievals}"
            )

        forbidden_reads = {
            path.replace(chr(92), "/") for path in task.trace_expectations.forbidden_read_paths
        }
        for event in recorder.tool_calls:
            if event.get("tool") != "read_file":
                continue
            path = str((event.get("input") or {}).get("file_path", "")).replace(chr(92), "/")
            if any(path == blocked or path.endswith("/" + blocked) for blocked in forbidden_reads):
                failures.append(f"forbidden path was read: {path}")

    return failures


def install_trace(agent: "Agent", recorder: TraceRecorder) -> None:
    original_execute = agent._execute_tool_call

    async def traced_execute(name: str, inp: dict) -> str:
        recorder.record("tool_call", tool=name, input=inp)
        start = time.perf_counter()
        try:
            result = await original_execute(name, inp)
        except Exception as exc:
            recorder.record("tool_result", tool=name, ok=False, error=str(exc), duration_ms=duration_ms(start))
            raise
        ok = not (result.startswith("Error") or result.startswith("Command failed"))
        recorder.record(
            "tool_result",
            tool=name,
            ok=ok,
            chars=len(result),
            duration_ms=duration_ms(start),
            preview=result[:500],
        )
        if not ok:
            recorder.record("tool_error", tool=name, preview=result[:500])
        memory_root = os.environ.get("COOLCODE_MEMORY_DIR")
        file_path = inp.get("file_path")
        if name == "read_file" and memory_root and file_path:
            try:
                if Path(file_path).resolve().is_relative_to(Path(memory_root).resolve()):
                    recorder.record("memory_retrieve", source="tool", path=str(file_path))
            except (OSError, ValueError):
                pass
        return result

    agent._execute_tool_call = traced_execute  # type: ignore[method-assign]


@contextlib.contextmanager
def pushd(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


@contextlib.contextmanager
def temporary_env(name: str, value: str):
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _history_chars(agent: "Agent") -> int:
    messages = agent._openai_messages if agent.use_openai else agent._anthropic_messages
    return len(json.dumps(messages, ensure_ascii=False, default=str))


def install_runtime_trace(
    agent: "Agent",
    recorder: TraceRecorder,
    *,
    compression_mode: str,
    memory_enabled: bool,
) -> None:
    original_compact = agent._compact_conversation

    async def traced_compact() -> None:
        before = _history_chars(agent)
        recorder.record(
            "compression_start",
            mode="autocompact",
            context_chars_before=before,
            last_input_tokens=agent.last_input_token_count,
            effective_window=agent.effective_window,
        )
        await original_compact()
        after = _history_chars(agent)
        recorder.record(
            "compression",
            mode="autocompact",
            context_chars_before=before,
            context_chars_after=after,
            chars_removed=max(0, before - after),
        )

    original_pipeline = agent._run_compression_pipeline

    def traced_pipeline() -> None:
        before = _history_chars(agent)
        original_pipeline()
        after = _history_chars(agent)
        if after < before:
            recorder.record(
                "compression",
                mode="pipeline",
                context_chars_before=before,
                context_chars_after=after,
                chars_removed=before - after,
            )

    if compression_mode == "off":
        async def no_compact() -> None:
            return None

        agent._check_and_compact = no_compact  # type: ignore[method-assign]
        agent._run_compression_pipeline = lambda: None  # type: ignore[method-assign]
    else:
        agent._compact_conversation = traced_compact  # type: ignore[method-assign]
        agent._run_compression_pipeline = traced_pipeline  # type: ignore[method-assign]

    original_consume = agent._consume_memory_prefetch_if_ready

    def traced_consume(messages: list) -> None:
        before = set(agent._already_surfaced_memories)
        original_consume(messages)
        for path in sorted(agent._already_surfaced_memories - before):
            recorder.record("memory_retrieve", source="prefetch", path=path)

    if memory_enabled:
        agent._consume_memory_prefetch_if_ready = traced_consume  # type: ignore[method-assign]
    else:
        agent._start_memory_prefetch_for_turn = lambda user_message, messages: None  # type: ignore[method-assign]
        agent._consume_memory_prefetch_if_ready = lambda messages: None  # type: ignore[method-assign]


@contextlib.contextmanager
def permission_trace(recorder: TraceRecorder):
    import coolcode.agent as agent_module
    import coolcode.tools as tools_module

    original = agent_module.check_permission

    def traced_check(tool_name: str, inp: dict, mode: str = "default", plan_file_path: str | None = None) -> dict:
        decision = original(tool_name, inp, mode, plan_file_path)
        recorder.record(
            "permission_decision",
            tool=tool_name,
            action=decision.get("action"),
            message=decision.get("message", ""),
            mode=mode,
            input=inp,
        )
        return decision

    tools_module._cached_rules = None
    agent_module.check_permission = traced_check
    try:
        yield
    finally:
        agent_module.check_permission = original
        tools_module._cached_rules = None


def trace_metrics(recorder: TraceRecorder) -> dict[str, Any]:
    permission_events = [
        event for event in recorder.events if event.get("event") == "permission_decision"
    ]
    actions: dict[str, int] = {}
    for event in permission_events:
        action = str(event.get("action", "unknown"))
        actions[action] = actions.get(action, 0) + 1

    compression_events = [
        event for event in recorder.events if event.get("event") == "compression"
    ]
    memory_events = [
        event for event in recorder.events if event.get("event") == "memory_retrieve"
    ]
    failed_tools = sum(
        1 for event in recorder.tool_results if not bool(event.get("ok"))
    )
    seen_reads: set[str] = set()
    duplicate_reads = 0
    for event in recorder.tool_calls:
        if event.get("tool") != "read_file":
            continue
        path = str((event.get("input") or {}).get("file_path", "")).replace(chr(92), "/")
        if path in seen_reads:
            duplicate_reads += 1
        seen_reads.add(path)

    return {
        "permission_decisions": len(permission_events),
        "permission_actions": actions,
        "compression_events": len(compression_events),
        "compression_chars_removed": sum(
            int(event.get("chars_removed", 0)) for event in compression_events
        ),
        "memory_retrievals": len(memory_events),
        "failed_tool_calls": failed_tools,
        "duplicate_reads": duplicate_reads,
    }


def classify_failures(reasons: list[str]) -> list[str]:
    labels: set[str] = set()
    for reason in reasons:
        if reason.startswith("validator failed"):
            labels.add("validator_failed")
        elif "compression" in reason:
            labels.add("compression_not_triggered")
        elif "permission" in reason or "denial" in reason:
            labels.add("permission_policy_failed")
        elif "forbidden file" in reason:
            labels.add("forbidden_file_modified")
        elif "memory" in reason:
            labels.add("required_memory_not_retrieved")
        elif "tool" in reason:
            labels.add("tool_error")
        elif "agent error" in reason:
            labels.add("runner_error")
        else:
            labels.add("task_assertion_failed")
    return sorted(labels)


async def run_agent_task(
    task: Task,
    workspace: Path,
    recorder: TraceRecorder,
    api: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, dict[str, Any]]:
    from coolcode.agent import Agent

    model = task.agent.model or api["model"]
    permission_mode = args.permission_mode or task.agent.permission_mode
    max_turns = args.max_turns if args.max_turns is not None else task.agent.max_turns
    max_cost = args.max_cost if args.max_cost is not None else task.agent.max_cost_usd

    async def confirm_fn(message: str) -> bool:
        recorder.record("confirmation", message=message, allowed=False)
        return False

    async def plan_approval_fn(plan_content: str) -> dict[str, Any]:
        recorder.record("plan_approval", choice="manual-execute", chars=len(plan_content))
        return {"choice": "manual-execute"}

    eval_prompt = (
        "You are running inside an isolated evaluation workspace. "
        "Only inspect and modify files in the current working directory. "
        "Use relative paths whenever possible, and do not edit files under the evals/fixtures source directory.\n\n"
        + task.prompt
    )

    agent: Agent | None = None
    with pushd(workspace):
        agent = Agent(
            permission_mode=permission_mode,
            model=model,
            thinking=task.agent.thinking,
            max_cost_usd=max_cost,
            max_turns=max_turns,
            api_base=api["api_base"] if api["use_openai"] else None,
            anthropic_base_url=api["api_base"] if not api["use_openai"] else None,
            api_key=api["api_key"],
            confirm_fn=confirm_fn,
        )
        agent.set_plan_approval_fn(plan_approval_fn)
        install_trace(agent, recorder)
        try:
            result = await agent.run_once(eval_prompt)
        finally:
            await agent.close()

    stats = {
        "turns": agent.current_turns,
        "tokens": {
            "input": agent.total_input_tokens,
            "output": agent.total_output_tokens,
            "cache_read": agent.total_cache_read_tokens,
            "cache_creation": agent.total_cache_creation_tokens,
        },
        "estimated_cost_usd": round(agent._get_current_cost_usd(), 6),
    }
    return result.get("text", ""), stats


async def run_specialized_agent_task(
    task: Task,
    workspace: Path,
    memory_dir: Path,
    recorder: TraceRecorder,
    api: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, dict[str, Any]]:
    from coolcode.agent import Agent
    from coolcode.memory import save_memory

    model = task.agent.model or api["model"]
    permission_mode = args.permission_mode or task.agent.permission_mode
    max_turns = args.max_turns if args.max_turns is not None else task.agent.max_turns
    max_cost = args.max_cost if args.max_cost is not None else task.agent.max_cost_usd

    async def confirm_fn(message: str) -> bool:
        recorder.record("confirmation", message=message, allowed=False)
        return False

    async def plan_approval_fn(plan_content: str) -> dict[str, Any]:
        recorder.record("plan_approval", choice="manual-execute", chars=len(plan_content))
        return {"choice": "manual-execute"}

    def make_agent() -> Agent:
        agent = Agent(
            permission_mode=permission_mode,
            model=model,
            thinking=task.agent.thinking,
            max_cost_usd=max_cost,
            max_turns=max_turns,
            api_base=api["api_base"] if api["use_openai"] else None,
            anthropic_base_url=api["api_base"] if not api["use_openai"] else None,
            api_key=api["api_key"],
            confirm_fn=confirm_fn,
        )
        if task.agent.effective_context_window is not None:
            agent.effective_window = task.agent.effective_context_window
        agent.set_plan_approval_fn(plan_approval_fn)
        install_trace(agent, recorder)
        install_runtime_trace(
            agent,
            recorder,
            compression_mode=task.agent.compression_mode,
            memory_enabled=task.agent.memory_enabled,
        )
        return agent

    prompt_prefix = (
        "You are running inside an isolated evaluation workspace. "
        "Only inspect and modify files in the current working directory. "
        "Use relative paths whenever possible, and do not edit files under the "
        "evals/fixtures source directory.\n\n"
    )
    prompts = [*task.prelude_prompts, task.prompt]
    outputs: list[str] = []
    total_turns = 0
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_creation = 0
    total_cost = 0.0

    recorder.record(
        "run_config",
        model=model,
        permission_mode=permission_mode,
        compression_mode=task.agent.compression_mode,
        effective_context_window=task.agent.effective_context_window,
        memory_enabled=task.agent.memory_enabled,
        prompt_count=len(prompts),
        reset_agent_between_prompts=task.reset_agent_between_prompts,
    )

    memory_dir.mkdir(parents=True, exist_ok=True)
    with temporary_env("COOLCODE_MEMORY_DIR", str(memory_dir.resolve())):
        with pushd(workspace):
            for entry in task.memory_entries:
                filename = save_memory(
                    str(entry["name"]),
                    str(entry.get("description", "")),
                    str(entry.get("type", "project")),
                    str(entry["content"]),
                )
                recorder.record("memory_write", source="fixture", filename=filename)

            with permission_trace(recorder):
                if task.reset_agent_between_prompts:
                    for index, prompt in enumerate(prompts):
                        agent = make_agent()
                        try:
                            result = await agent.run_once(prompt_prefix + prompt)
                            outputs.append(result.get("text", ""))
                        finally:
                            await agent.close()
                        total_turns += agent.current_turns
                        total_input += agent.total_input_tokens
                        total_output += agent.total_output_tokens
                        total_cache_read += agent.total_cache_read_tokens
                        total_cache_creation += agent.total_cache_creation_tokens
                        total_cost += agent._get_current_cost_usd()
                        recorder.record("prompt_end", index=index, turns=agent.current_turns)
                else:
                    agent = make_agent()
                    try:
                        for index, prompt in enumerate(prompts):
                            result = await agent.run_once(prompt_prefix + prompt)
                            outputs.append(result.get("text", ""))
                            recorder.record("prompt_end", index=index, turns=agent.current_turns)
                    finally:
                        await agent.close()
                    total_turns = agent.current_turns
                    total_input = agent.total_input_tokens
                    total_output = agent.total_output_tokens
                    total_cache_read = agent.total_cache_read_tokens
                    total_cache_creation = agent.total_cache_creation_tokens
                    total_cost = agent._get_current_cost_usd()

    return "\n\n--- prompt boundary ---\n\n".join(outputs), {
        "turns": total_turns,
        "tokens": {
            "input": total_input,
            "output": total_output,
            "cache_read": total_cache_read,
            "cache_creation": total_cache_creation,
        },
        "estimated_cost_usd": round(total_cost, 6),
    }


async def run_one_task(
    task: Task,
    *,
    run_dir: Path,
    api: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    task_dir = run_dir / "task_runs" / task.id
    task_dir.mkdir(parents=True, exist_ok=True)
    workspace_parent = run_dir / "workspaces" if args.keep_workspaces else Path(tempfile.mkdtemp(prefix="coolcode_eval_"))
    workspace = workspace_parent / task.id
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(task.fixture, workspace)

    trace_path = task_dir / "trace.jsonl"
    recorder = TraceRecorder(trace_path)
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    final_message = ""
    agent_stats: dict[str, Any] = {"turns": 0, "tokens": {}, "estimated_cost_usd": 0.0}
    before = collect_files(workspace)
    started = time.perf_counter()
    runner_error: str | None = None

    recorder.record(
        "task_start",
        task_id=task.id,
        category=task.category,
        suite=task.suite,
        variant=task.variant,
        episode_id=task.episode_id,
        risk_tags=task.risk_tags,
        dry_run=args.dry_run,
    )
    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            if args.dry_run:
                with pushd(workspace):
                    final_message = apply_oracle(task, workspace, recorder)
            else:
                final_message, agent_stats = await run_specialized_agent_task(
                    task,
                    workspace,
                    task_dir / "memory",
                    recorder,
                    api,
                    args,
                )
    except Exception as exc:
        runner_error = str(exc)
        stderr_buf.write(f"\nEval runner error: {exc}\n")
        recorder.record("task_error", error=str(exc))

    validator_commands: list[dict[str, Any]] = []
    for command in task.success.commands:
        result = run_validator_command(command, workspace, timeout=args.validation_timeout)
        validator_commands.append(result)
        recorder.record(
            "validator_command",
            command=command,
            exit_code=result["exit_code"],
            duration_ms=result["duration_ms"],
        )

    after = collect_files(workspace)
    diff_text, changed_files = make_diff(before, after)
    turns = int(agent_stats.get("turns", 0))
    failures = validate_task(
        task,
        workspace,
        recorder,
        changed_files,
        validator_commands,
        turns,
        dry_run=args.dry_run,
    )
    if runner_error:
        failures.insert(0, f"agent error: {runner_error}")
    runtime_seconds = round(time.perf_counter() - started, 3)
    passed = len(failures) == 0
    task_trace_metrics = trace_metrics(recorder)
    recorder.record("task_end", task_id=task.id, passed=passed, runtime_seconds=runtime_seconds)
    recorder.close()

    (task_dir / "stdout.txt").write_text(stdout_buf.getvalue(), encoding="utf-8")
    (task_dir / "stderr.txt").write_text(stderr_buf.getvalue(), encoding="utf-8")
    (task_dir / "final_message.txt").write_text(final_message, encoding="utf-8")
    (task_dir / "diff.patch").write_text(diff_text, encoding="utf-8")
    write_json(task_dir / "validators.json", validator_commands)

    result_payload = {
        "task_id": task.id,
        "category": task.category,
        "suite": task.suite,
        "variant": task.variant,
        "episode_id": task.episode_id,
        "risk_tags": task.risk_tags,
        "metadata": task.metadata,
        "passed": passed,
        "failure_reasons": failures,
        "failure_taxonomy": classify_failures(failures),
        "dry_run": args.dry_run,
        "runtime_seconds": runtime_seconds,
        "turns": agent_stats.get("turns", 0),
        "tokens": agent_stats.get("tokens", {}),
        "estimated_cost_usd": agent_stats.get("estimated_cost_usd", 0.0),
        "tool_call_count": len(recorder.tool_calls),
        "tool_counts": recorder.tool_counts,
        "trace_metrics": task_trace_metrics,
        "changed_files": changed_files,
        "validator_commands": [
            {k: v for k, v in command.items() if k not in {"stdout", "stderr"}}
            for command in validator_commands
        ],
        "artifacts": {
            "trace": str(trace_path),
            "diff": str(task_dir / "diff.patch"),
            "stdout": str(task_dir / "stdout.txt"),
            "stderr": str(task_dir / "stderr.txt"),
            "final_message": str(task_dir / "final_message.txt"),
            "validators": str(task_dir / "validators.json"),
            "memory": str(task_dir / "memory"),
        },
    }
    if args.keep_workspaces:
        result_payload["workspace"] = str(workspace)
    write_json(task_dir / "result.json", result_payload)

    if not args.keep_workspaces:
        shutil.rmtree(workspace_parent, ignore_errors=True)
    return result_payload


async def run(args: argparse.Namespace) -> int:
    load_dotenv(REPO_ROOT / ".env")
    api = resolve_api(args, dry_run=args.dry_run)
    tasks = select_tasks(load_tasks(args.tasks_dir, eval_root=EVAL_ROOT), args)
    run_id = make_run_id(args.output_name)
    run_dir = args.results_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Run ID: {run_id}")
    print(f"Mode: {'dry-run oracle' if args.dry_run else 'real API'}")
    print(f"Tasks: {', '.join(task.id for task in tasks)}")
    print(f"Results: {run_dir}")

    results: list[dict[str, Any]] = []
    for task in tasks:
        print(f"[eval] {task.id} ({task.category})")
        result = await run_one_task(task, run_dir=run_dir, api=api, args=args)
        results.append(result)
        print(f"  passed={result['passed']} tools={result['tool_call_count']} runtime={result['runtime_seconds']}s")

    metrics = aggregate_results(results)
    summary_payload = {
        "run_id": run_id,
        "dry_run": args.dry_run,
        "provider": api["provider"],
        "model": api["model"],
        "suite_filter": args.suite,
        "variant_filter": args.variant,
        "metrics": metrics,
        "tasks": [task.id for task in tasks],
    }
    write_json(run_dir / "summary.json", summary_payload)
    write_json(
        run_dir / "manifest.json",
        {
            "run_id": run_id,
            "provider": api["provider"],
            "model": api["model"],
            "dry_run": args.dry_run,
            "suite_filter": args.suite,
            "variant_filter": args.variant,
            "tasks": [
                {
                    "id": task.id,
                    "suite": task.suite,
                    "variant": task.variant,
                    "source": str(task.source_path),
                }
                for task in tasks
            ],
        },
    )
    write_tasks_jsonl(run_dir / "tasks.jsonl", results)
    write_summary_md(
        run_dir / "summary.md",
        run_id=run_id,
        dry_run=args.dry_run,
        provider=api["provider"],
        model=api["model"],
        metrics=metrics,
        results=results,
    )
    print(f"Summary: {run_dir / 'summary.md'}")
    return 0 if metrics["passed_tasks"] == metrics["total_tasks"] else 1


def main() -> None:
    configure_stdio()
    try:
        code = asyncio.run(run(parse_args()))
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
