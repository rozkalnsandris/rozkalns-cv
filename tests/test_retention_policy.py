from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RetentionPolicyContractTests(unittest.TestCase):
    def test_runtime_and_example_default_to_no_raw_chat_storage(self) -> None:
        config_source = (ROOT / "bot/config.py").read_text(encoding="utf-8")
        env_example = (ROOT / "bot/.env.example").read_text(encoding="utf-8")

        self.assertIn(
            '_integer(source, "CHAT_RETENTION_DAYS", 0, minimum=0, maximum=365)',
            config_source,
        )
        self.assertIn("CHAT_RETENTION_DAYS=0\n", env_example)
        self.assertNotIn("CHAT_RETENTION_DAYS=7\n", env_example)

    def test_factory_starts_and_closes_retention_service(self) -> None:
        app_source = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        entry_source = (ROOT / "bot/chat_entry.py").read_text(encoding="utf-8")
        self.assertIn("active_store.start_retention_maintenance()", app_source)
        self.assertIn("def close_app_services(", app_source)
        self.assertIn("store.close()", app_source)
        self.assertIn("atexit.register(close_app_services, app)", entry_source)


if __name__ == "__main__":
    unittest.main()
