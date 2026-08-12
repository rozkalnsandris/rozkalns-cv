from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))


class ExceptionResponsePrivacyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {
            "LLM_API_KEY": "test-llm-key",
            "LLM_MODEL": "deepseek-v4-flash",
            "CLIENT_KEY_SECRET": "A" * 43,
            "ASSISTANT_DB_PATH": str(Path(self.tmp.name) / "assistant.sqlite3"),
            "RATE_PER_IP_HOUR": "2",
            "DAILY_GLOBAL_CAP": "20",
            "CHAT_RETENTION_DAYS": "7",
            "TRUSTED_PROXY_CIDRS": "172.19.0.10/32",
            "TELEGRAM_TOKEN": "",
            "CHAT_ID": "",
            "TURNSTILE_SITE_KEY": "test-site-key",
            "TURNSTILE_SECRET_KEY": "test-secret-key",
            "TURNSTILE_HOSTNAMES": "rozkalns.net",
            "CONTACT_EMAIL": "person@example.com",
            "CONTACT_PHONE_DISPLAY": "+49 123 456789",
            "CONTACT_PHONE_URI": "+49123456789",
        }
        self.env_patch = patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        module_name = f"cv_exception_privacy_test_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, BOT / "app.py")
        assert spec and spec.loader
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = self.module
        self.addCleanup(sys.modules.pop, module_name, None)
        spec.loader.exec_module(self.module)
        self.client = self.module.app.test_client()
        self.addCleanup(self.module.close_app_services, self.module.app)

    def _admission_headers(self, address: str = "203.0.113.10") -> dict[str, str]:
        client_key = self.module.STORE.pseudonymize(
            address, self.module.CLIENT_KEY_SECRET
        )
        session = self.module.issue_session(
            client_key, self.module.CLIENT_KEY_SECRET
        )
        return {
            "X-Real-IP": address,
            "X-Chat-Admission": session,
        }

    def test_contact_validation_exception_text_is_not_exposed(self) -> None:
        internal_detail = "sensitive internal detail: /srv/cv/.env"
        with patch.object(
            self.module,
            "normalize_token",
            side_effect=self.module.ContactVerificationError(internal_detail),
        ):
            response = self.client.post(
                "/contact-reveal",
                json={"token": "candidate-token"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"error": "Turnstile token is invalid."},
        )
        self.assertNotIn(internal_detail, response.get_data(as_text=True))

    def test_chat_validation_exception_text_is_not_exposed(self) -> None:
        internal_detail = "sensitive internal detail: SELECT * FROM chats"
        with patch.object(
            self.module,
            "_parse_payload",
            side_effect=self.module.RequestValidationError(internal_detail),
        ):
            response = self.client.post(
                "/chat",
                json={"message": "Question", "history": []},
                headers=self._admission_headers(),
                environ_base={"REMOTE_ADDR": "172.19.0.10"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {
                "reply": (
                    "Invalid chat request: message or conversation history is "
                    "invalid or too long."
                )
            },
        )
        self.assertNotIn(internal_detail, response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
