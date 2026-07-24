# Resume Template For The Eval Harness

Use only measured numbers from real API runs. Do not report dry-run oracle numbers as agent performance.

## Before Real Baseline

Built a Python task-level Agent Eval Harness for a coding-agent CLI, covering repo fixture setup, isolated workspaces, tool trace capture, file diff capture, validator command execution, and summary report generation.

Implemented 5 deterministic Python bug-fix eval tasks with automatic pass/fail checks based on unit tests, target-file diffs, forbidden test edits, tool usage expectations, runtime, and per-task artifacts.

## After First Real API Baseline

Built a Python Agent Eval Harness that evaluates a coding agent through real API-driven repo tasks instead of self-reported completion. Ran N bug-fix/test-writing/refactor tasks and captured tool traces, file diffs, validator output, runtime, token usage, and estimated cost; baseline task success rate: X%.

## Early 5-Task Smoke

Run artifact:

```text
evals/results/2026-07-17_21-04-05_deepseek_baseline_bugfix_5/
```

Measured with `deepseek-v4-pro` through the OpenAI-compatible backend:

```text
Tasks: 5 Python bug-fix repo tasks
Passed: 5 / 5
Task success rate: 100.0%
Command pass rate: 100.0%
Average turns: 4.4
Average tool calls: 5.2
Average runtime: 16.364s
Average estimated cost: $0.028 / task
Total estimated cost: $0.1375
Forbidden tool violation rate: 0.0%
```

This was the early smoke run. Prefer the 20-task benchmark below for resumes.

## Current 20-Task Real API Baseline

```text
evals/results/2026-07-18_16-22-10_deepseek_baseline_20/
```

Measured with `deepseek-v4-pro` through the OpenAI-compatible backend:

```text
Tasks: 20 Python repo tasks
Categories: bugfix, test-writing, refactor, context, safety
Passed: 19 / 20
Task success rate: 95.0%
Command pass rate: 95.0%
Average turns: 5.0
Average tool calls: 6.2
Average runtime: 13.412s
Average estimated cost: $0.031 / task
Total estimated cost: $0.6233
Forbidden tool violation rate: 0.0%
```

## After One Improvement Round

Run artifact:

```text
evals/results/2026-07-18_16-46-49_deepseek_utf8_fix_20/
evals/results/compare_deepseek_baseline_vs_utf8_fix.md
```

Measured change:

```text
Fix: explicit UTF-8 file reads/writes in write_file and edit_file
Task success rate: 95.0% -> 100.0%
Test-writing success rate: 66.67% -> 100.0%
Average turns: 5.0 -> 4.55
Average tool calls: 6.2 -> 5.65
Average runtime: 13.412s -> 12.329s
Forbidden tool violation rate: 0.0% -> 0.0%
```

Resume bullet:

```text
Built a Python task-level Agent Eval Harness for a coding-agent CLI, running real DeepSeek API-driven repository tasks in isolated workspaces and automatically grading file diffs, unittest validators, tool traces, runtime, token usage, and cost across a 20-task benchmark. Used failure analysis to fix UTF-8 handling in agent file-edit tools, improving pass rate from 95.0% to 100.0%, reducing average tool calls from 6.2 to 5.65 and average runtime from 13.412s to 12.329s.
```

## Strong Project Description

CoolCode: Python coding-agent CLI with a task-level Agent Eval Harness. The harness spins up isolated repo fixtures, runs the real agent loop through API calls, records read/edit/shell tool traces, captures generated diffs, executes unit-test validators, and produces reproducible JSON/Markdown metrics for agent iteration.

## Metrics To Fill Later

- Total tasks: 20
- Categories: bugfix, test-writing, refactor, context, safety
- Real API model: deepseek-v4-pro
- Baseline success rate: 95.0%
- Improved success rate: 100.0%
- Avg turns: 4.55 after UTF-8 fix
- Avg tool calls: 5.65 after UTF-8 fix
- Avg runtime: 12.329s after UTF-8 fix
- Estimated cost per task: $0.03 after UTF-8 fix
- Most common failure classes: generated-source encoding issue in test-writing before UTF-8 tool fix
