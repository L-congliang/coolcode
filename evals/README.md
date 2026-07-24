# Python Agent Eval Harness

This directory contains a task-level evaluation harness for the CoolCode coding agent. It runs small repository tasks in isolated workspaces, lets the agent edit files with its normal tools, and grades the result with file diffs, unittest commands, and tool traces.

## What It Measures

- Task success rate across repo-level Python tasks.
- Validator command pass rate.
- Modified and forbidden file checks.
- Tool trajectory, including required and forbidden tool usage.
- Turns, tool calls, runtime, token usage, and estimated cost.
- Category-level performance for bugfix, test-writing, refactor, context, and safety tasks.

## Task Set

Phase 1 contains 20 Python tasks:

- 9 bugfix tasks.
- 3 test-writing tasks.
- 3 refactor tasks.
- 3 context/multi-file tasks.
- 2 safety-boundary tasks.

Task definitions live in `tasks/`. Each task points at a fixture repository under `fixtures/`, defines success criteria, trace expectations, and an oracle edit used only for dry-run smoke tests.

## Run A Dry-Run Smoke Test

From the project root:

```powershell
uv run python -m evals.runner --dry-run --output-name dry_run_20
```

Dry-run mode does not call an LLM. It applies the task oracle edits and verifies that the harness, validators, diff capture, trace capture, and report generation work.

## Run A Real API Eval

Configure `.env` at the repo root:

```dotenv
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.deepseek.com
COOLCODE_MODEL=deepseek-v4-pro
```

Then run:

```powershell
uv run python -m evals.runner --output-name deepseek_20 --max-turns 8 --max-cost 0.2
```

Real API mode sends the task prompt, fixture contents accessed through tools, and tool outputs to the configured model provider. Result artifacts are written under `results/<timestamp>_<output-name>/`.

## Result Artifacts

Each run writes:

- `summary.md`: human-readable run summary.
- `summary.json`: aggregate metrics.
- `tasks.jsonl`: one JSON result record per task.
- `task_runs/<task_id>/trace.jsonl`: tool and validator trace.
- `task_runs/<task_id>/diff.patch`: captured file diff.
- `task_runs/<task_id>/stdout.txt` and `stderr.txt`: agent execution logs.
- `task_runs/<task_id>/final_message.txt`: final model response.

## Compare Two Runs

Use `compare.py` to generate a before/after delta report:

```powershell
uv run python -m evals.compare results/<baseline-run> results/<candidate-run> --output results/comparison.md
```

This is the main source for resume metrics such as success-rate improvement, tool-call reduction, and category-level regressions.

## Resume Framing

Strong resume wording should use real API results, not dry-run results. A good final bullet after a 20-task real run looks like:

> Built a Python task-level Agent Eval Harness for a coding-agent CLI, running real DeepSeek API-driven repository tasks in isolated workspaces and automatically grading file diffs, unittest validators, tool traces, runtime, token usage, and cost across a 20-task benchmark.

After a baseline/improvement comparison, add the actual deltas from `compare.py`.
