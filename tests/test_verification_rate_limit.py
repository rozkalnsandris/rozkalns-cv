from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

import app as app_module  # noqa: E402
from config import Settings, SettingsError, VerificationRateConfig  # noqa: E402
from contact import ContactConfig  # noqa: E402
from storage import AssistantStore  # noqa: E402


CONTACT = ContactConfig(
    site_key="test-site-key",
    secret_key="test-secret-key",
    email="andris@example.invalid",
    phone_display="+49 170 1234567",
    phone_uri="+491701234567",
    hostnames=frozenset({"rozkalns.net"}),
)


class MutableClock:
    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def make_settings(db_path: str) -> Settings:
    return Settings.from_env(
        {
            "LLM_API_KEY": "test-provider-key",
            "CLIENT_KEY_SECRET": "A" * 43,
            "ASSISTANT_DB_PATH": db_path,
            "CHAT_RETENTION_DAYS": "0",
            "TRUSTED_PROXY_CIDRS": "172.19.0.10/32",
        }
    )


def make_store(path: str, clock=None) -> AssistantStore:
    return AssistantStore(
        path,
        per_client_hour=8,
        daily_global_cap=200,
        chat_retention_days=0,
        **({"clock": clock} if clock is not None else {}),
    )


class VerificationRateLimitTests(unittest.TestCase):
    def test_config_defaults_and_bounds(self) -> None:
        config = VerificationRateConfig.from_env({})
        self.assertEqual(config.per_client_hour, 60)
        self.assertEqual(config.global_hour, 600)
        with self.assertRaisesRegex(SettingsError, "TURNSTILE_VERIFY_PER_IP_HOUR"):
            VerificationRateConfig.from_env(
                {"TURNSTILE_VERIFY_PER_IP_HOUR": "0"}
            )
        with self.assertRaisesRegex(SettingsError, "TURNSTILE_VERIFY_GLOBAL_HOUR"):
            VerificationRateConfig.from_env(
                {"TURNSTILE_VERIFY_GLOBAL_HOUR": "100001"}
            )

    def test_verification_client_limit_persists_and_does_not_consume_chat_quota(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "assistant.sqlite3")
            clock = MutableClock(1_700_000_000)
            first = make_store(path, clock)
            self.assertTrue(
                first.reserve_verification(
                    "client-a", per_client_hour=1, global_hour=10
                ).allowed
            )
            second = make_store(path, clock)
            denied = second.reserve_verification(
                "client-a", per_client_hour=1, global_hour=10
            )
            self.assertFalse(denied.allowed)
            self.assertEqual(denied.reason, "client")
            self.assertGreater(denied.retry_after, 0)
            self.assertTrue(second.reserve("client-a").allowed)

    def test_verification_global_limit_is_shared_across_clients_and_resets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "assistant.sqlite3")
            clock = MutableClock(1_700_000_000)
            store = make_store(path, clock)
            self.assertTrue(
                store.reserve_verification(
                    "client-a", per_client_hour=10, global_hour=1
                ).allowed
            )
            denied = store.reserve_verification(
                "client-b", per_client_hour=10, global_hour=1
            )
            self.assertFalse(denied.allowed)
            self.assertEqual(denied.reason, "global")
            clock.value += 3601
            self.assertTrue(
                store.reserve_verification(
                    "client-b", per_client_hour=10, global_hour=1
                ).allowed
            )

    def _make_app(self, directory: str, limit: int = 1):
        path = str(Path(directory) / "assistant.sqlite3")
        store = make_store(path)
        flask_app = app_module.create_app(
            make_settings(path),
            store=store,
            contact_config=CONTACT,
            system_prompt="test prompt",
            verification_rate=VerificationRateConfig(
                per_client_hour=limit,
                global_hour=10,
            ),
            start_maintenance=False,
        )
        self.addCleanup(app_module.close_app_services, flask_app)
        return flask_app, store

    def test_contact_reveal_limit_blocks_siteverify_and_sets_retry_after(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flask_app, _store = self._make_app(directory)
            with patch.object(
                app_module, "verify_turnstile", return_value=True
            ) as verify:
                client = flask_app.test_client()
                first = client.post(
                    "/contact-reveal", json={"token": "token-one"}
                )
                second = client.post(
                    "/contact-reveal", json={"token": "token-two"}
                )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 429)
            self.assertGreater(int(second.headers["Retry-After"]), 0)
            self.assertEqual(verify.call_count, 1)

    def test_chat_admission_limit_blocks_siteverify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flask_app, _store = self._make_app(directory)
            with patch.object(
                app_module, "verify_chat_turnstile", return_value=True
            ) as verify:
                client = flask_app.test_client()
                first = client.post(
                    "/chat-admission", json={"token": "token-one"}
                )
                second = client.post(
                    "/chat-admission", json={"token": "token-two"}
                )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 429)
            self.assertGreater(int(second.headers["Retry-After"]), 0)
            self.assertEqual(verify.call_count, 1)

    def test_verification_store_failure_fails_closed_before_siteverify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            flask_app, store = self._make_app(directory)
            with (
                patch.object(
                    store,
                    "reserve_verification",
                    side_effect=RuntimeError("db down"),
                ),
                patch.object(
                    app_module, "verify_turnstile", return_value=True
                ) as verify,
            ):
                response = flask_app.test_client().post(
                    "/contact-reveal", json={"token": "token-one"}
                )
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("db down", response.get_data(as_text=True))
            self.assertEqual(verify.call_count, 0)


if __name__ == "__main__":
    unittest.main()
