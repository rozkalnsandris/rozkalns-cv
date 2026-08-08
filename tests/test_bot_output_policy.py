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

from chat_policy import BLOCKED_CONTACT_REPLY  # noqa: E402


class FakeUpstreamResponse:
    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = False):
        rows = []
        for chunk in self.chunks:
            payload = {
                "choices": [
                    {"delta": {"content": chunk}, "finish_reason": None}
                ]
            }
            rows.append(f"data: {json.dumps(payload)}")
        rows.append('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}')
        rows.append("data: [DONE]")
        return iter(rows)


class BotOutputPolicyIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = str(Path(self.tmp.name) / "assistant.sqlite3")
        env = {
            "LLM_API_KEY": "test-llm-key",
            "LLM_MODEL": "deepseek-v4-flash",
            "CLIENT_KEY_SECRET": "A" * 43,
            "ASSISTANT_DB_PATH": self.db_path,
            "RATE_PER_IP_HOUR": "20",
            "DAILY_GLOBAL_CAP": "100",
            "CHAT_RETENTION_DAYS": "7",
            "TRUSTED_PROXY_CIDRS": "172.19.0.10/32",
            "CONTACT_EMAIL": "andris@rozkalns.net",
            "CONTACT_PHONE_DISPLAY": "+49 170 1234567",
            "CONTACT_PHONE_URI": "tel:+491701234567",
            "TELEGRAM_TOKEN": "",
            "CHAT_ID": "",
        }
        self.env_patch = patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        module_name = f"cv_app_output_policy_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, BOT / "app.py")
        assert spec and spec.loader
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = self.module
        self.addCleanup(sys.modules.pop, module_name, None)
        spec.loader.exec_module(self.module)
        self.addCleanup(self.module.STORE.close)
        self.client = self.module.app.test_client()

    def _post_chunks(self, chunks: list[str]):
        def upstream(*args, **kwargs):
            return FakeUpstreamResponse(chunks)

        with patch.object(self.module.requests, "post", side_effect=upstream):
            response = self.client.post(
                "/chat",
                json={"message": "How can I contact Andris?", "history": []},
                headers={"X-Real-IP": "203.0.113.10"},
                environ_base={"REMOTE_ADDR": "172.19.0.10"},
                buffered=True,
            )
            response.get_data()
        return response

    def test_cross_chunk_runtime_phone_is_blocked_before_browser_and_storage(self) -> None:
        response = self._post_chunks(["Call +49 170 ", "123", "4567 now."])
        body = response.get_data(as_text=True)
        self.assertEqual(body, BLOCKED_CONTACT_REPLY)
        self.assertNotIn("491701234567", "".join(body.split()))

        with sqlite3.connect(self.db_path) as connection:
            answer = connection.execute(
                "SELECT answer FROM chats ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
        self.assertEqual(answer, BLOCKED_CONTACT_REPLY)
        self.assertNotIn("1234567", answer)

    def test_public_recruiting_email_remains_allowed(self) -> None:
        response = self._post_chunks(["Email: andris@rozkalns.net"])
        self.assertEqual(
            response.get_data(as_text=True),
            "Email: andris@rozkalns.net",
        )

    def test_numbered_whatsapp_target_is_blocked(self) -> None:
        response = self._post_chunks(["Open https://wa.", "me/491701234567"])
        self.assertEqual(
            response.get_data(as_text=True),
            BLOCKED_CONTACT_REPLY,
        )


if __name__ == "__main__":
    unittest.main()
