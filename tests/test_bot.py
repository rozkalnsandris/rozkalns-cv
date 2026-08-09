from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from notifier import TelegramNotifier  # noqa: E402


class FakeUpstreamResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = False):
        return iter(
            [
                'data: {"choices":[{"delta":{"reasoning_content":"hidden chain"},"finish_reason":null}]}',
                'data: {"choices":[{"delta":{},"finish_reason":null}]}',
                'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}',
                'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}',
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
                "data: [DONE]",
            ]
        )


class FakeTelegramResponse:
    def raise_for_status(self) -> None:
        return None


class BotBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = str(Path(self.tmp.name) / "assistant.sqlite3")
        env = {
            "LLM_API_KEY": "test-llm-key",
            "LLM_MODEL": "deepseek-v4-flash",
            "CLIENT_KEY_SECRET": "A" * 43,
            "ASSISTANT_DB_PATH": self.db_path,
            "RATE_PER_IP_HOUR": "2",
            "DAILY_GLOBAL_CAP": "20",
            "CHAT_RETENTION_DAYS": "7",
            "TRUSTED_PROXY_CIDRS": "172.19.0.10/32",
            "TELEGRAM_TOKEN": "",
            "CHAT_ID": "",
        }
        self.env_patch = patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        module_name = f"cv_app_test_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, BOT / "app.py")
        assert spec and spec.loader
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = self.module
        self.addCleanup(sys.modules.pop, module_name, None)
        spec.loader.exec_module(self.module)
        self.client = self.module.app.test_client()
        self.addCleanup(self.module.close_app_services, self.module.app)

    def _admission_header(self, address: str) -> dict[str, str]:
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

    def _post(self, message: str, history=None, *, address="203.0.113.10"):
        captured: list[dict] = []

        def upstream(*args, **kwargs):
            captured.append(kwargs["json"])
            return FakeUpstreamResponse()

        with patch.object(self.module.requests, "post", side_effect=upstream):
            response = self.client.post(
                "/chat",
                json={"message": message, "history": history or []},
                headers=self._admission_header(address),
                environ_base={"REMOTE_ADDR": "172.19.0.10"},
                buffered=True,
            )
            response.get_data()
        return response, captured

    def test_current_message_is_sent_upstream_exactly_once(self) -> None:
        response, captured = self._post(
            "Current question",
            history=[
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"},
                {"role": "user", "content": "Current question"},
            ],
        )
        self.assertEqual(response.status_code, 200)
        messages = captured[0]["messages"]
        self.assertEqual(
            [row["role"] for row in messages],
            ["system", "user", "assistant", "user"],
        )
        self.assertEqual(
            sum(row["content"] == "Current question" for row in messages), 1
        )

    def test_unpaired_failed_browser_turn_is_not_forwarded(self) -> None:
        response, captured = self._post(
            "New question",
            history=[
                {"role": "user", "content": "Failed question"},
                {"role": "user", "content": "New question"},
            ],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["role"] for row in captured[0]["messages"]],
            ["system", "user"],
        )
        self.assertEqual(captured[0]["messages"][-1]["content"], "New question")

    def test_v4_request_contract_is_explicit_non_thinking(self) -> None:
        response, captured = self._post("Question")
        self.assertEqual(response.status_code, 200)
        payload = captured[0]
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["max_tokens"], self.module.MAX_RESPONSE_TOKENS)
        self.assertEqual(payload["temperature"], 0.4)
        self.assertNotIn("reasoning_effort", payload)

    def test_v4_reasoning_content_is_never_forwarded(self) -> None:
        response, _ = self._post("Question")
        body = response.get_data(as_text=True)
        self.assertEqual(body, "Hello world")
        self.assertNotIn("hidden chain", body)

    def test_only_supported_v4_models_are_allowed(self) -> None:
        self.assertEqual(
            self.module.SUPPORTED_LLM_MODELS,
            frozenset({"deepseek-v4-flash", "deepseek-v4-pro"}),
        )
        self.assertIn(self.module.LLM_MODEL, self.module.SUPPORTED_LLM_MODELS)
        self.assertNotIn("deepseek-chat", self.module.SUPPORTED_LLM_MODELS)
        self.assertNotIn("deepseek-reasoner", self.module.SUPPORTED_LLM_MODELS)

    def test_invalid_payload_does_not_consume_quota(self) -> None:
        address = "203.0.113.10"
        response = self.client.post(
            "/chat",
            json={"message": "", "history": []},
            environ_base={"REMOTE_ADDR": "172.19.0.10"},
            headers=self._admission_header(address),
        )
        self.assertEqual(response.status_code, 400)
        with sqlite3.connect(self.db_path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM rate_events").fetchone()[0]
        self.assertEqual(count, 0)

    def test_trusted_proxy_uses_normalized_real_ip(self) -> None:
        with self.module.app.test_request_context(
            "/chat",
            headers={
                "X-Real-IP": "203.0.113.40",
                "X-Forwarded-For": "198.51.100.99",
            },
            environ_base={"REMOTE_ADDR": "172.19.0.10"},
        ):
            self.assertEqual(self.module._resolve_client_address(), "203.0.113.40")

    def test_direct_peer_cannot_spoof_forwarding_headers(self) -> None:
        with self.module.app.test_request_context(
            "/chat",
            headers={
                "X-Real-IP": "203.0.113.40",
                "X-Forwarded-For": "198.51.100.99",
                "CF-Connecting-IP": "192.0.2.99",
            },
            environ_base={"REMOTE_ADDR": "192.0.2.10"},
        ):
            self.assertEqual(self.module._resolve_client_address(), "192.0.2.10")

    def test_two_public_visitors_have_independent_limits(self) -> None:
        self.module.STORE.per_client_hour = 1
        first, _ = self._post("Question one", address="203.0.113.1")
        second, _ = self._post("Question two", address="203.0.113.2")
        denied, _ = self._post("Again", address="203.0.113.1")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(denied.status_code, 429)
        self.assertIn("Retry-After", denied.headers)

    def test_success_response_includes_rate_metadata(self) -> None:
        response, _ = self._post("Question")
        self.assertEqual(response.headers["X-RateLimit-Limit"], "2")
        self.assertEqual(response.headers["X-RateLimit-Remaining"], "1")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_chat_database_contains_pseudonym_not_raw_ip(self) -> None:
        address = "203.0.113.77"
        response, _ = self._post("Question", address=address)
        self.assertEqual(response.status_code, 200)
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT client_key, question, answer FROM chats"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertNotEqual(row[0], address)
        self.assertNotIn(address, json.dumps(row))

    def test_telegram_notification_is_redacted_by_default(self) -> None:
        notifier = TelegramNotifier(
            token="token",
            chat_id="chat",
            include_content=False,
            max_workers=1,
        )
        self.addCleanup(notifier.close)
        with patch(
            "notifier.requests.post",
            return_value=FakeTelegramResponse(),
        ) as mocked:
            notifier._send("client-key", "private question", "private answer")
        text = mocked.call_args.kwargs["data"]["text"]
        self.assertIn("client-key", text)
        self.assertNotIn("private question", text)
        self.assertNotIn("private answer", text)


if __name__ == "__main__":
    unittest.main()
