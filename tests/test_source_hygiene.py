from __future__ import annotations

from pathlib import Path
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
