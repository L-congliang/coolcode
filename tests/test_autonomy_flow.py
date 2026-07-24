"""Control-flow tests for the two-stage Auto Mode classifier.

Stubs the per-stage classifier query (no network) and drives
Agent._classify_tool_call directly, covering: stage-1 gate,
stage-1→stage-2 escalation, denial counting, and fail-closed parsing.

Agent imports the anthropic/openai SDKs, so this module skips cleanly when those
deps aren't installed (the pure-function suite in test_autonomy.py has no such
dependency and always runs). Run with `python -B tests/test_autonomy_flow.py`."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_PYTHON_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PYTHON_DIR))

try:
    from coolcode.agent import Agent
    HAVE_DEPS = True
except Exception:
    HAVE_DEPS = False


_memory_tmp = None
_previous_memory_dir = None


def setUpModule():
    global _memory_tmp, _previous_memory_dir
    _previous_memory_dir = os.environ.get("COOLCODE_MEMORY_DIR")
    _memory_tmp = tempfile.TemporaryDirectory(prefix="coolcode_test_memory_")
    os.environ["COOLCODE_MEMORY_DIR"] = _memory_tmp.name


def tearDownModule():
    if _previous_memory_dir is None:
        os.environ.pop("COOLCODE_MEMORY_DIR", None)
    else:
        os.environ["COOLCODE_MEMORY_DIR"] = _previous_memory_dir
    if _memory_tmp is not None:
        _memory_tmp.cleanup()


def _mk_agent(responses):
    """An Agent whose classifier query returns canned per-stage responses.
    Returns (agent, calls) where calls['n'] counts stage queries made."""
    agent = Agent(api_key="test-key", permission_mode="auto")
    calls = {"n": 0}

    async def _stub(system, user, max_tokens):
        i = calls["n"]
        calls["n"] += 1
        if i < len(responses):
            return responses[i]
        return "<block>yes</block><reason>[fallback] ran out of canned responses</reason>"

    agent._run_classifier_query = _stub
    return agent, calls


@unittest.skipUnless(HAVE_DEPS, "anthropic/openai not installed")
class TestTwoStageFlow(unittest.IsolatedAsyncioTestCase):
    async def test_stage1_allow_one_call(self):
        agent, calls = _mk_agent(["<block>no</block>"])
        r = await agent._classify_tool_call("run_shell", {"command": "echo hi"})
        self.assertEqual(r["action"], "allow")
        self.assertEqual(calls["n"], 1, "stage 2 must not run when stage 1 allows")

    async def test_stage1_block_then_stage2_allow(self):
        agent, calls = _mk_agent([
            "<block>yes</block><reason>[Git Push to Default Branch] main</reason>",
            "<block>no</block>",
        ])
        r = await agent._classify_tool_call("run_shell", {"command": "echo hi"})
        self.assertEqual(r["action"], "allow")
        self.assertEqual(calls["n"], 2, "stage 2 must run after a stage 1 block")

    async def test_stage2_block_denial_counted_once(self):
        agent, calls = _mk_agent([
            "<block>yes</block><reason>[Git Push to Default Branch] a</reason>",
            "<block>yes</block><reason>[Git Push to Default Branch] b</reason>",
        ])
        r = await agent._classify_tool_call("run_shell", {"command": "echo hi"})
        self.assertEqual(r["action"], "deny")
        self.assertIn("[Auto Mode]", r["message"])
        self.assertEqual(calls["n"], 2)
        self.assertEqual(agent.auto_consecutive_denials, 1, "one blocked action → one denial")

    async def test_stage2_unparseable_blocks(self):
        agent, _ = _mk_agent([
            "<block>yes</block><reason>[X] a</reason>",
            "garbage, not a verdict",
        ])
        r = await agent._classify_tool_call("run_shell", {"command": "echo hi"})
        self.assertEqual(r["action"], "deny")

    async def test_fast_path_skips_classifier(self):
        agent, calls = _mk_agent(["<block>yes</block><reason>should not be used</reason>"])
        r = await agent._classify_tool_call("read_file", {"file_path": "x"})
        self.assertEqual(r["action"], "allow")
        self.assertEqual(calls["n"], 0, "read-only tools must not call the classifier")


if __name__ == "__main__":
    unittest.main(verbosity=2)
