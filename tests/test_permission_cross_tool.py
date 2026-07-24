import json
import os
from pathlib import Path
import tempfile
import unittest

import coolcode.tools as tools


class CrossToolPermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_cwd = Path.cwd()
        os.chdir(self.temp_dir.name)
        settings_dir = Path(".claude")
        settings_dir.mkdir()
        settings = {
            "permissions": {
                "deny": [
                    "read_file(.env)",
                    "edit_file(protected.txt)",
                    "write_file(protected.txt)",
                ]
            }
        }
        (settings_dir / "settings.json").write_text(
            json.dumps(settings), encoding="utf-8"
        )
        tools._cached_rules = None

    def tearDown(self):
        tools._cached_rules = None
        os.chdir(self.old_cwd)
        self.temp_dir.cleanup()

    def test_shell_redirection_to_protected_file_is_denied(self):
        result = tools.check_permission(
            "run_shell", {"command": "echo changed > protected.txt"}, "acceptEdits"
        )
        self.assertEqual(result["action"], "deny")

    def test_powershell_write_to_protected_file_is_denied(self):
        result = tools.check_permission(
            "run_shell",
            {"command": "Set-Content -Path protected.txt -Value changed"},
            "acceptEdits",
        )
        self.assertEqual(result["action"], "deny")

    def test_shell_read_of_sensitive_file_is_denied(self):
        result = tools.check_permission(
            "run_shell", {"command": "type .env"}, "acceptEdits"
        )
        self.assertEqual(result["action"], "deny")

    def test_grep_of_sensitive_file_is_denied(self):
        result = tools.check_permission(
            "grep_search", {"pattern": ".*", "path": ".env"}, "acceptEdits"
        )
        self.assertEqual(result["action"], "deny")

    def test_absolute_sensitive_path_is_denied(self):
        absolute_env = str((Path.cwd() / ".env").resolve())
        result = tools.check_permission(
            "read_file", {"file_path": absolute_env}, "acceptEdits"
        )
        self.assertEqual(result["action"], "deny")

    def test_absolute_protected_edit_path_is_denied(self):
        absolute_file = str((Path.cwd() / "protected.txt").resolve())
        result = tools.check_permission(
            "edit_file",
            {"file_path": absolute_file, "old_string": "a", "new_string": "b"},
            "acceptEdits",
        )
        self.assertEqual(result["action"], "deny")

    def test_subagent_cannot_launder_sensitive_read(self):
        result = tools.check_permission(
            "agent",
            {"prompt": "Read secret data from .env", "type": "general"},
            "acceptEdits",
        )
        self.assertEqual(result["action"], "deny")

    def test_unrelated_safe_shell_command_is_allowed(self):
        result = tools.check_permission(
            "run_shell", {"command": "python -m unittest"}, "acceptEdits"
        )
        self.assertEqual(result["action"], "allow")


if __name__ == "__main__":
    unittest.main()
