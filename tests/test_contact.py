from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

import contact


class FakeSiteverifyResponse:
    def __init__(self, payload, status_error: Exception | None = None):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self) -> None:
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.payload


class ContactVerificationTests(unittest.TestCase):
    def config(self) -> contact.ContactConfig:
        return contact.ContactConfig(
            site_key="site-key",
            secret_key="secret-key",
            email="person@example.com",
            phone_display="+49 123 456789",
            phone_uri="+49123456789",
            hostnames=frozenset({"rozkalns.net"}),
        )

    def test_token_validation_is_bounded(self) -> None:
        for value in (None, "", " ", "x" * (contact.MAX_TOKEN_CHARS + 1)):
            with self.subTest(value=value):
                with self.assertRaises(contact.ContactVerificationError):
                    contact.normalize_token(value)
        self.assertEqual(contact.normalize_token(" token "), "token")

    def test_success_requires_matching_action_and_hostname(self) -> None:
        calls = []

        def post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeSiteverifyResponse(
                {
                    "success": True,
                    "action": contact.TURNSTILE_ACTION,
                    "hostname": "rozkalns.net",
                }
            )

        self.assertTrue(
            contact.verify_turnstile(
                "token", "203.0.113.9", self.config(), post=post
            )
        )
        self.assertEqual(calls[0][0], contact.SITEVERIFY_URL)
        self.assertEqual(calls[0][1]["data"]["secret"], "secret-key")
        self.assertEqual(calls[0][1]["data"]["response"], "token")
        self.assertEqual(calls[0][1]["data"]["remoteip"], "203.0.113.9")

    def test_wrong_action_or_hostname_fails_closed(self) -> None:
        for payload in (
            {"success": True, "action": "login", "hostname": "rozkalns.net"},
            {
                "success": True,
                "action": contact.TURNSTILE_ACTION,
                "hostname": "example.com",
            },
            {"success": False},
        ):
            with self.subTest(payload=payload):
                self.assertFalse(
                    contact.verify_turnstile(
                        "token",
                        "203.0.113.9",
                        self.config(),
                        post=lambda *args, **kwargs: FakeSiteverifyResponse(payload),
                    )
                )

    def test_siteverify_transport_failure_is_fail_closed(self) -> None:
        def post(*args, **kwargs):
            raise requests.Timeout("timeout")

        with self.assertRaises(contact.ContactVerificationError):
            contact.verify_turnstile(
                "token", "203.0.113.9", self.config(), post=post
            )


class ContactEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {
            "LLM_API_KEY": "test-llm-key",
            "CLIENT_KEY_SECRET": "test-client-secret",
            "ASSISTANT_DB_PATH": str(Path(self.tmp.name) / "assistant.sqlite3"),
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

        module_name = f"cv_contact_app_test_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, BOT / "app.py")
        assert spec and spec.loader
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = self.module
        self.addCleanup(sys.modules.pop, module_name, None)
        spec.loader.exec_module(self.module)
        self.client = self.module.app.test_client()

    def test_config_exposes_only_public_sitekey(self) -> None:
        response = self.client.get("/contact-config")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"configured": True, "sitekey": "test-site-key"},
        )
        self.assertNotIn("test-secret-key", response.get_data(as_text=True))
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_verified_token_reveals_contact(self) -> None:
        with patch.object(self.module, "verify_turnstile", return_value=True) as verify:
            response = self.client.post(
                "/contact-reveal",
                json={"token": "valid-token"},
                headers={"X-Real-IP": "203.0.113.55"},
                environ_base={"REMOTE_ADDR": "172.19.0.10"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "email": "person@example.com",
                "phone": "+49 123 456789",
                "phone_uri": "+49123456789",
            },
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        verify.assert_called_once_with(
            "valid-token", "203.0.113.55", self.module.CONTACT_CONFIG
        )

    def test_failed_token_does_not_reveal_contact(self) -> None:
        with patch.object(self.module, "verify_turnstile", return_value=False):
            response = self.client.post(
                "/contact-reveal",
                json={"token": "bad-token"},
                environ_base={"REMOTE_ADDR": "192.0.2.20"},
            )
        self.assertEqual(response.status_code, 403)
        body = response.get_data(as_text=True)
        self.assertNotIn("person@example.com", body)
        self.assertNotIn("+49123456789", body)

    def test_invalid_token_is_rejected_before_siteverify(self) -> None:
        with patch.object(self.module, "verify_turnstile") as verify:
            response = self.client.post("/contact-reveal", json={"token": ""})
        self.assertEqual(response.status_code, 400)
        verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
