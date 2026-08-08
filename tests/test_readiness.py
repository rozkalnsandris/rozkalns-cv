from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from readiness import check_local_readiness  # noqa: E402


SUPPORTED = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})


class LocalReadinessTests(unittest.TestCase):
    def _check(self, path: Path, **overrides):
        kwargs = {
            "llm_api_key": "provider-key",
            "client_key_secret": "A" * 43,
            "llm_model": "deepseek-v4-flash",
            "supported_models": SUPPORTED,
        }
        kwargs.update(overrides)
        return check_local_readiness(path, **kwargs)

    def test_ready_sqlite_is_readable_writable_and_probe_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assistant.sqlite3"
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE durable_state (id INTEGER)")
            result = self._check(path)
            self.assertTrue(result.ready)
            self.assertIsNone(result.reason)
            with sqlite3.connect(path) as connection:
                probe = connection.execute(
                    "SELECT name FROM sqlite_master WHERE name = ?",
                    ("__cvbot_readiness_probe",),
                ).fetchone()
                durable = connection.execute(
                    "SELECT name FROM sqlite_master WHERE name = ?",
                    ("durable_state",),
                ).fetchone()
            self.assertIsNone(probe)
            self.assertIsNotNone(durable)

    def test_missing_mandatory_chat_config_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assistant.sqlite3"
            for field in ("llm_api_key", "client_key_secret"):
                with self.subTest(field=field):
                    result = self._check(path, **{field: ""})
                    self.assertFalse(result.ready)
                    self.assertEqual(result.reason, "config")
            result = self._check(path, llm_model="unsupported-model")
            self.assertFalse(result.ready)
            self.assertEqual(result.reason, "config")

    def test_corrupt_sqlite_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assistant.sqlite3"
            path.write_bytes(b"not-a-sqlite-database")
            result = self._check(path)
            self.assertFalse(result.ready)
            self.assertEqual(result.reason, "storage")

    def test_unavailable_sqlite_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "assistant.sqlite3"
            with patch(
                "readiness.sqlite3.connect",
                side_effect=sqlite3.OperationalError("unavailable"),
            ):
                result = self._check(path)
            self.assertFalse(result.ready)
            self.assertEqual(result.reason, "storage")


if __name__ == "__main__":
    unittest.main()
