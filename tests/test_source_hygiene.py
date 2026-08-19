from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-source.sh"
GITIGNORE = ROOT / ".gitignore"


class SourceHygieneTests(unittest.TestCase):
    def test_retired_source_writers_are_absent(self) -> None:
        for path in (
            ROOT / "update.sh",
            ROOT / "update_cv-1.sh",
            ROOT / "docker-compose.network.yml",
        ):
            self.assertFalse(path.exists(), path)

    def test_retired_github_runner_bootstrap_paths_fail_closed(self) -> None:
        for path in (
            ROOT / "runner" / "activate-github-main-deploy.sh",
            ROOT / "runner" / "install-github-main-deploy.sh",
            ROOT / "runner" / "install-github-cv-runner.sh",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertIn("LEGACY_GITHUB_RUNNER_BOOTSTRAP_RETIRED=true", text)
            for forbidden in (
                "gh api",
                "./config.sh",
                "./svc.sh",
                "useradd",
                "visudo",
                "systemctl",
                "sudo bash",
            ):
                self.assertNotIn(forbidden, text)
            completed = subprocess.run(
                ["bash", str(path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(completed.returncode, 64, completed.stdout)
            self.assertIn("retired", completed.stdout.lower())

    def test_validator_routes_bytecode_outside_source_tree(self) -> None:
        text = VALIDATOR.read_text(encoding="utf-8")
        for marker in (
            "PYTHONPYCACHEPREFIX=\"$VALIDATION_TMP/pycache\"",
            "generated Python artifact must not exist",
            "validation dirtied source tree",
            "repository-local .venv is generated state",
        ):
            self.assertIn(marker, text)

    def test_generated_python_state_is_ignored(self) -> None:
        text = GITIGNORE.read_text(encoding="utf-8")
        for marker in (
            ".venv/",
            "__pycache__/",
            "*.py[cod]",
            ".mypy_cache/",
            ".ruff_cache/",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
