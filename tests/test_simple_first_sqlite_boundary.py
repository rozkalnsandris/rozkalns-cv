from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

import app as app_module  # noqa: E402
from config import Settings, VerificationRateConfig  # noqa: E402
from contact import ContactConfig  # noqa: E402
from storage import AssistantStore  # noqa: E402


CONTACT = ContactConfig(
    site_key="test-public-site-key",
    secret_key="test-secret-key",
    email="person@example.com",
    phone_display="+49 123 456789",
    phone_uri="+49123456789",
    hostnames=frozenset({"rozkalns.net"}),
)


def make_public(path: Path, *, retention: int = 0, per_hour: int = 2):
    settings = Settings.from_env({
        "LLM_API_KEY": "",
        "CLIENT_KEY_SECRET": "A" * 43,
        "ASSISTANT_DB_PATH": str(path),
        "CHAT_RETENTION_DAYS": str(retention),
        "TELEGRAM_TOKEN": "",
        "CHAT_ID": "",
    })
    return app_module.create_app(
        settings,
        contact_config=CONTACT,
        system_prompt="unit test public mode",
        verification_rate=VerificationRateConfig(
            per_client_hour=per_hour, global_hour=3
        ),
        public_only=True,
    )


class SimpleFirstSQLiteBoundaryTests(unittest.TestCase):
    def test_cold_start_and_passive_gets_never_create_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "absent" / "assistant.sqlite3"
            app = make_public(path)
            self.addCleanup(app_module.close_app_services, app)
            self.assertFalse(path.parent.exists())
            for route in ("/health", "/health/live", "/health/ready", "/contact-config"):
                response = app.test_client().get(route)
                self.assertEqual(response.status_code, 200, route)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertFalse(path.parent.exists(), route)
            self.assertEqual(
                app.test_client().get("/health/ready").get_json(), {"ready": True}
            )
            self.assertFalse(path.exists())

    def test_public_mode_has_no_assistant_endpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            app = make_public(Path(directory) / "assistant.sqlite3")
            self.addCleanup(app_module.close_app_services, app)
            for route in ("/chat", "/chat-config", "/chat-admission"):
                self.assertEqual(app.test_client().get(route).status_code, 404)
                self.assertEqual(app.test_client().post(route).status_code, 404)

    def test_preexisting_chat_content_survives_zero_retention_public_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assistant.sqlite3"
            store = AssistantStore(
                path, per_client_hour=8, daily_global_cap=50,
                chat_retention_days=365,
            )
            store.record_chat("pseudo", "old-question", "old-answer")
            app = make_public(path, retention=0)
            self.addCleanup(app_module.close_app_services, app)
            for route in ("/health", "/health/ready", "/contact-config"):
                self.assertEqual(app.test_client().get(route).status_code, 200)
            with sqlite3.connect(path) as connection:
                count = connection.execute("SELECT COUNT(*) FROM chats").fetchone()
            self.assertEqual(count, (1,))

    def test_contact_attempt_lazily_creates_only_verification_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assistant.sqlite3"
            app = make_public(path, per_hour=1)
            self.addCleanup(app_module.close_app_services, app)
            client = app.test_client()
            self.assertFalse(path.exists())
            with patch.object(app_module, "verify_turnstile", return_value=True) as verify:
                success = client.post("/contact-reveal", json={"token": "valid-token"})
                throttled = client.post("/contact-reveal", json={"token": "valid-token"})
            self.assertEqual(success.status_code, 200)
            self.assertEqual(success.get_json()["phone_uri"], CONTACT.phone_uri)
            self.assertEqual(throttled.status_code, 429)
            verify.assert_called_once()
            with sqlite3.connect(path) as conn:
                tables = {
                    r[0] for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                number = conn.execute(
                    "SELECT COUNT(*) FROM verification_events"
                ).fetchone()
            self.assertEqual(tables, {"verification_events"})
            self.assertEqual(number, (1,))

    def test_denied_contact_and_invalid_token_do_not_leak_information(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assistant.sqlite3"
            app = make_public(path)
            self.addCleanup(app_module.close_app_services, app)
            client = app.test_client()
            invalid = client.post("/contact-reveal", json={"token": ""})
            self.assertEqual(invalid.status_code, 400)
            self.assertFalse(path.exists())
            with patch.object(app_module, "verify_turnstile", return_value=False):
                denied = client.post("/contact-reveal", json={"token": "valid-token"})
            self.assertEqual(denied.status_code, 403)
            self.assertNotIn(CONTACT.phone_uri, denied.get_data(as_text=True))

    def test_contact_store_unavailable_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assistant.sqlite3"
            app = make_public(path)
            self.addCleanup(app_module.close_app_services, app)
            with patch.object(
                app.extensions["cvbot"]["store"],
                "reserve_verification",
                side_effect=sqlite3.OperationalError("unavailable"),
            ), patch.object(app_module, "verify_turnstile") as verified:
                response = app.test_client().post(
                    "/contact-reveal", json={"token": "valid-token"}
                )
            self.assertEqual(response.status_code, 503)
            verified.assert_not_called()

    def test_runtime_entrypoint_explicit_and_full_mode_unchanged(self):
        supervisor = (ROOT / "deploy/simple-deploy/supervise.py").read_text("utf-8")
        entry = (ROOT / "bot/chat_entry.py").read_text("utf-8")
        nginx = (ROOT / "deploy/simple-deploy/nginx.conf").read_text("utf-8")
        self.assertIn('"chat_entry:create_public_app()"', supervisor)
        self.assertIn("create_base_app(public_only=True)", entry)
        self.assertIn("create_base_app()", entry)
        for route in ("/api/chat", "/api/chat-config", "/api/chat-admission"):
            self.assertIn("location = " + route + " { return 404; }", nginx)


if __name__ == "__main__":
    unittest.main()
