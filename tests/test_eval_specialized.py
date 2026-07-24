from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from evals.metrics import aggregate_results
from evals.task_schema import AgentConfig, Task, TraceExpectations
from coolcode.memory import get_memory_dir, list_memories, save_memory


class SpecializedEvalSchemaTest(unittest.TestCase):
    def test_specialized_defaults_are_backward_compatible(self):
        task = Task(
            id="demo",
            category="bugfix",
            fixture=Path("."),
            prompt="fix it",
        )

        self.assertEqual(task.suite, "general")
        self.assertEqual(task.variant, "default")
        self.assertEqual(task.agent.compression_mode, "default")
        self.assertTrue(task.agent.memory_enabled)
        self.assertEqual(task.trace_expectations.min_compression_events, 0)

    def test_specialized_agent_and_trace_fields(self):
        agent = AgentConfig(
            compression_mode="on",
            effective_context_window=7000,
            memory_enabled=False,
        )
        trace = TraceExpectations(
            required_permission_actions=["deny"],
            min_permission_denials=1,
            min_memory_retrievals=1,
        )

        self.assertEqual(agent.effective_context_window, 7000)
        self.assertFalse(agent.memory_enabled)
        self.assertEqual(trace.required_permission_actions, ["deny"])


class SpecializedMetricsTest(unittest.TestCase):
    def test_safety_confusion_matrix(self):
        base = {
            "category": "safety",
            "suite": "safety",
            "variant": "policy_on",
            "passed": True,
            "tool_call_count": 1,
            "turns": 1,
            "runtime_seconds": 0.1,
            "tokens": {"input": 1, "output": 1},
            "estimated_cost_usd": 0.0,
            "validator_commands": [],
            "failure_reasons": [],
            "failure_taxonomy": [],
        }
        deny = {
            **base,
            "task_id": "deny",
            "metadata": {"expected_permission_action": "deny"},
            "trace_metrics": {"permission_actions": {"deny": 1}},
        }
        allow = {
            **base,
            "task_id": "allow",
            "metadata": {"expected_permission_action": "allow"},
            "trace_metrics": {"permission_actions": {"allow": 1}},
        }

        metrics = aggregate_results([deny, allow])
        safety = metrics["specialized"]["safety"]
        self.assertEqual(safety["dangerous_operation_block_rate"], 100.0)
        self.assertEqual(safety["safe_operation_false_block_rate"], 0.0)


class MemoryIsolationTest(unittest.TestCase):
    def test_memory_directory_override(self):
        previous = os.environ.get("COOLCODE_MEMORY_DIR")
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["COOLCODE_MEMORY_DIR"] = tmp
            try:
                filename = save_memory(
                    "Eval policy",
                    "Synthetic test memory",
                    "project",
                    "POLICY=TEST",
                )
                self.assertEqual(get_memory_dir(), Path(tmp).resolve())
                self.assertTrue((Path(tmp) / filename).exists())
                self.assertEqual(len(list_memories()), 1)
            finally:
                if previous is None:
                    os.environ.pop("COOLCODE_MEMORY_DIR", None)
                else:
                    os.environ["COOLCODE_MEMORY_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
