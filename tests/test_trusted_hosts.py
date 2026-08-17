from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

import app as app_module  # noqa: E402
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


class TrustedHostsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        settings = Settings.from_env(
            {
                "LLM_API_KEY": "test-provider-key",
                "CLIENT_KEY_SECRET": "A" * 43,
                "ASSISTANT_DB_PATH": str(Path(self.temp.name) / "assistant.sqlite3"),
                "CHAT_RETENTION_DAYS": "0",
                "TELEGRAM_TOKEN": "",
                "CHAT_ID": "",
            }
        )
        self.app = app_module.create_app(
            settings,
            contact_config=EMPTY_CONTACT,
            system_prompt="test prompt",
            start_maintenance=False,
        )
        self.addCleanup(app_module.close_app_services, self.app)
        self.client = self.app.test_client()

    def test_factory_configures_exact_trusted_hosts(self) -> None:
        self.assertEqual(
            self.app.config["TRUSTED_HOSTS"],
            ["rozkalns.net", "localhost", "cvbot", "127.0.0.1"],
        )

    def test_public_local_and_container_hosts_are_accepted(self) -> None:
        for host in (
            "rozkalns.net",
            "localhost",
            "localhost:5000",
            "cvbot",
            "cvbot:5000",
            "127.0.0.1",
            "127.0.0.1:5000",
        ):
            with self.subTest(host=host):
                response = self.client.get("/health", headers={"Host": host})
                self.assertEqual(response.status_code, 200)

    def test_docker_readiness_host_remains_accepted(self) -> None:
        response = self.client.get(
            "/health/ready", headers={"Host": "localhost:5000"}
        )
        self.assertEqual(response.status_code, 200)

    def test_unknown_host_fails_before_route_logic(self) -> None:
        response = self.client.post(
            "/chat",
            headers={"Host": "attacker.example"},
            json={"message": "hello"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
