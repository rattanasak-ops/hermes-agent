import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "worktree-lifecycle" / "shortcut_visibility_check.py"
PAYLOAD = ROOT / "team-shortcuts" / "payload"
VAULT = Path(os.environ.get("HERMES_VAULT_PATH", str(PAYLOAD)))


class ShortcutVisibilityTests(unittest.TestCase):
    def run_check(self, vault: Path, payload: Path):
        return subprocess.run(
            [sys.executable, str(CHECKER), "--vault", str(vault), "--payload", str(payload), "--json"],
            text=True, capture_output=True, check=False,
        )

    def test_real_source_and_payload_pass(self):
        result = self.run_check(VAULT, PAYLOAD)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('"shortcut_visibility": "33/33"', result.stdout)
        self.assertIn('"direct_integrations": "18/18"', result.stdout)
        self.assertIn('"worktree_auto_create": "0/33"', result.stdout)
        self.assertIn('"owner_branch_policy": "33/33"', result.stdout)

    def test_new_registry_shortcut_cannot_escape_contract_check(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "vault"
            import shutil
            shutil.copytree(VAULT, fake)
            registry = fake / "ai-context" / "prompt-shortcut-registry.md"
            skill = fake / "skills" / "prompt-shortcuts" / "SKILL.md"
            new_row = "| `Use Future Shortcut` | `future` | `references/future.md` |\n"
            registry.write_text(registry.read_text(encoding="utf-8") + new_row, encoding="utf-8")
            skill.write_text(skill.read_text(encoding="utf-8") + new_row, encoding="utf-8")
            result = self.run_check(fake, PAYLOAD)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("contract_missing_shortcut:Use Future Shortcut", result.stdout)

    def test_shortcut_auto_open_rule_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "vault"
            (fake / "skills" / "prompt-shortcuts" / "references").mkdir(parents=True)
            # Copying only the direct inputs is sufficient for a negative fixture.
            import shutil
            shutil.copytree(VAULT / "skills" / "prompt-shortcuts", fake / "skills" / "prompt-shortcuts", dirs_exist_ok=True)
            (fake / "ai-context").mkdir()
            shutil.copy2(VAULT / "ai-context" / "prompt-shortcut-registry.md", fake / "ai-context")
            target = fake / "skills" / "prompt-shortcuts" / "references" / "use-new-chat.md"
            target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "## Worktree แบบอ่านและจัดการของเดิมเท่านั้น",
                    "งานเขียนใหม่ต้องเรียก `hermes-new-chat open`\n\n## Worktree แบบอ่านและจัดการของเดิมเท่านั้น",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.run_check(fake, PAYLOAD)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("active_conflict", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
