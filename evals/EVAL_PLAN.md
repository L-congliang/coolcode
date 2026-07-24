# Python Agent Eval Harness Plan

## Goal

Build a Python-only task-level evaluation harness for CoolCode.

The harness should evaluate whether the agent can finish real coding tasks in an isolated repo workspace, not just whether individual functions pass unit tests. Each task should run the agent, capture tool traces, verify file changes and test results, and produce metrics that can be used for engineering iteration and resume-ready quantitative results.

The first version should focus on the Python implementation under `coolcode`. TypeScript parity is out of scope.

## What To Evaluate

The evaluation should cover these agent capabilities:

1. Agent loop
   - Model response to tool call.
   - Tool execution.
   - Tool result feedback.
   - Continued reasoning until final answer or budget stop.

2. File editing workflow
   - `read_file`, `grep_search`, `edit_file`, `write_file`, `run_shell`.
   - Read-before-edit behavior.
   - Correct diff and final file state.
   - Ability to run tests and fix failures.

3. Permission and safety behavior
   - Plan mode blocks writes and shell commands.
   - Dangerous shell commands require confirmation or are denied.
   - `dontAsk` mode denies risky actions.
   - Forbidden tools are not used in restricted tasks.

4. Context handling
   - Large file reads.
   - Large grep or shell output.
   - Tool result persistence and truncation.
   - Compression path keeps enough information for task completion.

5. Memory behavior
   - Save project/user preference as memory.
   - Recall memory in a later task.
   - Follow remembered instruction without re-stating it in the prompt.

6. Skill and sub-agent behavior
   - Skill discovery and invocation.
   - Read-only explore/plan sub-agent behavior.
   - Custom agent types can be added later.

7. MCP behavior
   - Defer to phase 2.
   - Evaluate stdio MCP discovery and tool routing once the base harness is stable.

## Initial Task Set

Start with 20 to 30 tasks. Keep fixtures small and deterministic.

| Category | Count | Example | Main Metrics |
| --- | ---: | --- | --- |
| Bug Fix | 8-10 | Fix a Python bug and make pytest pass | task success, pytest pass |
| Test Writing | 5-6 | Add tests for an existing function | pytest pass, file assertion |
| Refactor | 4-5 | Remove duplication while preserving behavior | pytest pass, diff constraints |
| File Edit | 3-5 | Modify CLI/config/docs precisely | file assertions, forbidden tool use |
| Permission | 4-5 | Verify plan/dontAsk/dangerous command behavior | block rate, policy correctness |
| Context | 2-3 | Work with large files or long command output | success, compression triggered |
| Memory | 2-3 | Save and recall project/user preference | recall success, instruction adherence |

Do not start with MCP or complex multi-agent tasks. Add them after the first stable baseline.

## Directory Layout

Use this structure:

```text
evals/
  EVAL_PLAN.md
  runner.py
  task_schema.py
  trace.py
  metrics.py
  report.py

  tasks/
    bugfix_001.yaml
    bugfix_002.yaml
    testwrite_001.yaml
    permission_001.yaml
    context_001.yaml
    memory_001.yaml

  fixtures/
    bugfix_001/
      repo/
    bugfix_002/
      repo/
    testwrite_001/
      repo/

  results/
    2026-07-17_001/
      summary.md
      summary.json
      tasks.jsonl
      task_runs/
        bugfix_001/
          trace.jsonl
          result.json
          diff.patch
          stdout.txt
          stderr.txt
          final_message.txt
```

`tasks/` stores task definitions.  
`fixtures/` stores clean source repos for each task.  
`results/` stores immutable run outputs. Each evaluation run gets a timestamped directory.

## Task Definition Format

Use YAML for readability once PyYAML is available. Phase 1 uses JSON task files to keep the harness zero-dependency beyond the existing project dependencies. A task should describe the fixture, prompt, agent options, success checks, and trace expectations.

Example:

```yaml
id: bugfix_001
category: bugfix
fixture: fixtures/bugfix_001/repo
prompt: "Fix the division bug in calculator.py and make all pytest tests pass."

agent:
  permission_mode: acceptEdits
  max_turns: 8
  max_cost_usd: 0.2
  model: null

success:
  commands:
    - "python -m pytest -q"
  file_contains:
    calculator.py:
      - "ZeroDivisionError"
  file_not_contains: {}

trace_expectations:
  required_tools:
    - read_file
    - edit_file
    - run_shell
  forbidden_tools:
    - write_file
  max_turns: 8
```

Recommended task fields:

```yaml
id: string
category: bugfix | test_writing | refactor | file_edit | permission | context | memory | mcp | skill
fixture: string
prompt: string
agent:
  permission_mode: default | plan | acceptEdits | bypassPermissions | dontAsk | auto
  max_turns: int
  max_cost_usd: float
  model: optional string
success:
  commands: list[string]
  file_contains: map[path, list[string]]
  file_not_contains: map[path, list[string]]
  expected_exit_code: optional int
trace_expectations:
  required_tools: list[string]
  forbidden_tools: list[string]
  max_tool_calls: optional int
  max_turns: optional int
```

## Runner Flow

`runner.py` should:

1. Load `.env` from repo root.
2. Resolve API config:
   - Prefer `ANTHROPIC_API_KEY` if set.
   - Use OpenAI-compatible backend when `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set.
   - Allow CLI overrides for model, task subset, and output directory.
3. Load task YAML files from `evals/tasks`.
4. For each task:
   - Create an isolated temp workspace.
   - Copy the fixture repo into the workspace.
   - Initialize git in the workspace for diff capture if needed.
   - Run the Python `Agent` in that workspace.
   - Feed the task prompt.
   - Capture tool calls, tool results, stdout, stderr, runtime, token usage, and final message.
   - Run success commands after the agent stops.
   - Check file assertions.
   - Check trace expectations.
   - Save `trace.jsonl`, `result.json`, `diff.patch`, `stdout.txt`, `stderr.txt`, and `final_message.txt`.
5. Aggregate all task results into `tasks.jsonl`, `summary.json`, and `summary.md`.

## Trace Events

Add a small trace recorder so eval results are inspectable. The first implementation can instrument `Agent._execute_tool_call`.

Trace event examples:

```json
{"event":"task_start","task_id":"bugfix_001","category":"bugfix"}
{"event":"tool_call","tool":"read_file","input":{"file_path":"calculator.py"}}
{"event":"tool_result","tool":"read_file","ok":true,"chars":1842,"duration_ms":4}
{"event":"tool_call","tool":"edit_file","input":{"file_path":"calculator.py"}}
{"event":"tool_result","tool":"edit_file","ok":true,"chars":512,"duration_ms":7}
{"event":"validator_command","command":"python -m pytest -q","exit_code":0}
{"event":"task_end","task_id":"bugfix_001","passed":true}
```

Avoid storing full tool outputs in summary files. Store full outputs only in per-task artifacts when useful, and truncate long values in trace events.

## Metrics

Compute at least these metrics:

```text
total_tasks
passed_tasks
task_success_rate
pytest_pass_rate
avg_turns
avg_tool_calls
avg_runtime_seconds
avg_input_tokens
avg_output_tokens
avg_estimated_cost_usd
forbidden_tool_violation_rate
dangerous_action_block_rate
context_task_success_rate
memory_task_success_rate
```

Per-category metrics:

```text
bugfix_success_rate
test_writing_success_rate
refactor_success_rate
permission_success_rate
context_success_rate
memory_success_rate
```

Efficiency metrics:

```text
median_tool_calls
median_turns
median_runtime_seconds
tools_per_successful_task
```

## Result Files

Each run should produce:

### `summary.md`

Human-readable report:

```markdown
# Eval Summary

- Run ID: 2026-07-17_001
- Model: claude-opus-4-6
- Total tasks: 30
- Passed: 24
- Success rate: 80.0%
- Avg turns: 4.7
- Avg tool calls: 9.3
- Avg runtime: 38.2s

## By Category

| Category | Passed | Total | Rate |
| --- | ---: | ---: | ---: |
| bugfix | 8 | 10 | 80.0% |

## Failures

| Task | Category | Reason |
| --- | --- | --- |
| context_002 | context | pytest failed after compression |
```

### `summary.json`

Machine-readable aggregate metrics.

### `tasks.jsonl`

One task result per line for later analysis.

### `task_runs/<task_id>/result.json`

Full single-task result.

### `task_runs/<task_id>/trace.jsonl`

Tool and validation events.

### `task_runs/<task_id>/diff.patch`

Final file diff produced by the agent.

## Baseline And Improvement Loop

The harness is valuable only if it enables comparison.

Recommended workflow:

1. Baseline run
   - Do not change agent logic.
   - Run all initial tasks.
   - Save results as `results/<date>_baseline`.

2. Failure analysis
   - Group failures by cause:
     - bad file search
     - bad edit
     - did not run tests
     - context lost
     - permission denied incorrectly
     - memory not recalled

3. Agent improvement
   - Modify one subsystem at a time.
   - Good first targets:
     - edit feedback and quote normalization
     - tool result truncation
     - compression thresholds
     - run_shell guidance
     - memory recall injection

4. Re-run the same task set
   - Save results as `results/<date>_after_<change>`.
   - Compare against baseline.

5. Resume-ready metrics
   - Only use measured deltas from repeatable runs.

Example resume statement after real measurements:

```text
Built a Python Agent Eval Harness with 30 repo-level coding tasks covering bug fixes,
test generation, refactoring, permission safety, long context, and memory recall.
Captured pytest results, file diffs, tool traces, and runtime metrics; used failure
analysis to improve file editing and context handling, raising task success from X%
to Y% and reducing average tool calls from A to B.
```

## Implementation Phases

### Phase 1: Minimal Working Harness

Deliverables:

- `task_schema.py`
- `runner.py`
- `trace.py`
- `metrics.py`
- `report.py`
- 5 bugfix fixtures
- 5 task YAML files
- `summary.json` and `summary.md`

Success condition:

- One command runs all 5 tasks.
- Each task creates result artifacts.
- Summary includes pass rate, avg turns, avg tool calls, and runtime.

### Phase 2: Broader Task Coverage

Deliverables:

- 20-30 total tasks.
- Add test writing, refactor, file edit, permission, context, and memory tasks.
- Add category-level metrics.

Success condition:

- First real baseline is reproducible.
- Failures are grouped by cause.

### Phase 3: Agent Instrumentation And Optimization

Deliverables:

- Cleaner trace hooks in `Agent`.
- Token/cost capture in results.
- Failure analysis report.
- One or two targeted agent improvements.

Success condition:

- Same eval set shows measurable improvement.
- Summary report has before/after comparison.

### Phase 4: Resume Packaging

Deliverables:

- `evals/README.md`
- Example `summary.md`
- One short architecture diagram or textual flow.
- Resume bullets based on measured numbers.

Success condition:

- A reviewer can understand what was evaluated, how it was evaluated, and what improved.

## CLI Shape

Target command:

```bash
cd python
python -m evals.runner --tasks all --model claude-opus-4-6
```

Useful options:

```bash
python -m evals.runner --category bugfix
python -m evals.runner --task bugfix_001
python -m evals.runner --limit 5
python -m evals.runner --output-name baseline
python -m evals.runner --permission-mode acceptEdits
```

## Notes

- Use real API calls for final baseline and improvement runs.
- Keep a mock-mode option later if cost becomes a problem.
- Keep fixtures small so evaluation is cheap and deterministic.
- Do not write resume metrics until at least one baseline and one repeated run exist.
- Always store the exact task set and result artifacts for reproducibility.
