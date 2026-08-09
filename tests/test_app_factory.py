from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from app import close_app_services, create_app  # noqa: E402
from config import Settings  # noqa: E402
from contact import ContactConfig  # noqa: E402


EMPTY_CONTACT = ContactConfig(
    site_key="",
    secret_key="",
    email="",
    phone_display="",
    phone_uri="",
    hostnames=frozenset({"rozkalns.net"}),
)


def make_settings(db_path: str) -> Settings:
    return Settings.from_env(
        {
            "LLM_API_KEY": "test-provider-key",
            "CLIENT_KEY_SECRET": "A" * 43,
            "ASSISTANT_DB_PATH": db_path,
            "CHAT_RETENTION_DAYS": "0",
            "TELEGRAM_TOKEN": "",
            "CHAT_ID": "",
        }
    )


class AppFactoryTests(unittest.TestCase):
    def test_import_app_does_not_require_runtime_secret(self) -> None:
        env = os.environ.copy()
        env.pop("CLIENT_KEY_SECRET", None)
        result = subprocess.run(
            [sys.executable, "-c", "import app"],
            cwd=BOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_factory_creates_isolated_service_graphs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = create_app(
                make_settings(str(Path(directory) / "first.sqlite3")),
                contact_config=EMPTY_CONTACT,
                system_prompt="test prompt",
                start_maintenance=False,
            )
            second = create_app(
                make_settings(str(Path(directory) / "second.sqlite3")),
                contact_config=EMPTY_CONTACT,
                system_prompt="test prompt",
                start_maintenance=False,
            )
            self.addCleanup(close_app_services, first)
            self.addCleanup(close_app_services, second)

            self.assertIsNot(first, second)
            first_services = first.extensions["cvbot"]
            second_services = second.extensions["cvbot"]
            self.assertIsNot(first_services["store"], second_services["store"])
            self.assertIsNot(first_services["notifier"], second_services["notifier"])
            self.assertIsNot(first_services["provider"], second_services["provider"])
            self.assertEqual(
                {rule.rule for rule in first.url_map.iter_rules()},
                {rule.rule for rule in second.url_map.iter_rules()},
            )
            self.assertIn("/chat", {rule.rule for rule in first.url_map.iter_rules()})
            self.assertIn(
                "/chat-admission", {rule.rule for rule in first.url_map.iter_rules()}
            )


if __name__ == "__main__":
    unittest.main()
