from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RetentionPolicyContractTests(unittest.TestCase):
    def test_runtime_and_example_default_to_no_raw_chat_storage(self) -> None:
        app_source = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        env_example = (ROOT / "bot/.env.example").read_text(encoding="utf-8")

        self.assertIn(
            'CHAT_RETENTION_DAYS = int(os.getenv("CHAT_RETENTION_DAYS", "0"))',
            app_source,
        )
        self.assertIn("CHAT_RETENTION_DAYS=0\n", env_example)
        self.assertNotIn("CHAT_RETENTION_DAYS=7\n", env_example)

    def test_runtime_starts_independent_retention_maintenance(self) -> None:
        app_source = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        self.assertIn("STORE.start_retention_maintenance()", app_source)
        self.assertIn("atexit.register(STORE.close)", app_source)


if __name__ == "__main__":
    unittest.main()
