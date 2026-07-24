# Agent Eval Experiment Report

## Goal

Evaluate the CoolCode coding agent on task-level repository workflows that resemble agent engineering intern work: bug fixing, test writing, refactoring, multi-file context use, and safety-boundary compliance.

## Benchmark

- Language: Python
- Task count: 20
- Categories: bugfix, test-writing, refactor, context, safety
- Grading signals: unittest validators, file diff checks, forbidden file checks, required/forbidden tool traces, runtime, turns, token usage, and estimated cost

## Baseline Run

- Run directory: `results/2026-07-18_16-22-10_deepseek_baseline_20`
- Provider: `openai-compatible`
- Model: `deepseek-v4-pro`
- Success rate: 95.0% (19/20)
- Command pass rate: 95.0%
- Avg turns: 5.0
- Avg tool calls: 6.2
- Avg runtime: 13.412s
- Avg estimated cost: $0.031 per task
- Total estimated cost: $0.6233
- Main failure category: test-writing failed once because tool writes used the Windows default encoding; a non-ASCII comment was persisted as invalid source bytes and broke `python -m unittest -q`.

## Improvement Run

- Run directory: `results/2026-07-18_16-46-49_deepseek_utf8_fix_20`
- Provider: `openai-compatible`
- Model: `deepseek-v4-pro`
- Change tested: explicit UTF-8 reads/writes in `write_file` and `edit_file`.
- Success rate: 100.0% (20/20)
- Command pass rate: 100.0%
- Avg turns: 4.55
- Avg tool calls: 5.65
- Avg runtime: 12.329s
- Avg estimated cost: $0.03 per task
- Total estimated cost: $0.6028
- Main failure categories: none in this run.

## Before/After Summary

- Comparison report: `results/compare_deepseek_baseline_vs_utf8_fix.md`
- Success rate delta: +5.0 percentage points.
- Avg tool-call delta: -0.55 calls per task.
- Avg runtime delta: -1.083s per task.
- Safety violation delta: 0.0 percentage points.
- Most improved category: test-writing, from 66.67% to 100.0%.
- Most fragile category: test-writing, because generated tests can include comments/characters that exercise tool encoding and source parsing behavior.

## Resume Bullets

- Built a Python task-level Agent Eval Harness for a coding-agent CLI, running real API-driven repository tasks in isolated workspaces and automatically grading file diffs, unittest validators, tool traces, runtime, token usage, and cost.
- Designed a 20-task Python benchmark covering bug fixing, test writing, refactoring, multi-file context use, and safety-boundary compliance.
- Ran real DeepSeek API evaluations and improved benchmark pass rate from 95.0% to 100.0% by fixing UTF-8 handling in agent file-edit tools; reduced average tool calls from 6.2 to 5.65 and average runtime from 13.412s to 12.329s.
