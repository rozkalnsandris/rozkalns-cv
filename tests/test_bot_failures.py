from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))


class UpstreamHttpFailure:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        raise requests.HTTPError("synthetic upstream 503")

    def iter_lines(self, decode_unicode: bool = False):
        return iter(())


class BotFailureBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = str(Path(self.tmp.name) / "assistant.sqlite3")
        env = {
            "LLM_API_KEY": "test-llm-key",
            "CLIENT_KEY_SECRET": "A" * 43,
            "ASSISTANT_DB_PATH": self.db_path,
            "RATE_PER_IP_HOUR": "20",
            "DAILY_GLOBAL_CAP": "100",
            "CHAT_RETENTION_DAYS": "7",
            "MAX_HISTORY_TURNS": "2",
            "MAX_INPUT_CHARS": "50",
            "TRUSTED_PROXY_CIDRS": "172.19.0.10/32",
            "TELEGRAM_TOKEN": "",
            "CHAT_ID": "",
        }
        self.env_patch = patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        module_name = f"cv_app_failure_test_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, BOT / "app.py")
        assert spec and spec.loader
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = self.module
        self.addCleanup(sys.modules.pop, module_name, None)
        spec.loader.exec_module(self.module)
        self.addCleanup(self.module.STORE.close)
        self.client = self.module.app.test_client()

    def post(self, payload):
        return self.client.post(
            "/chat",
            json=payload,
            headers={"X-Real-IP": "203.0.113.10"},
            environ_base={"REMOTE_ADDR": "172.19.0.10"},
            buffered=True,
        )

    def table_count(self, table: str) -> int:
        with sqlite3.connect(self.db_path) as connection:
            return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def test_upstream_timeout_streams_safe_message_without_retention(self) -> None:
        with patch.object(
            self.module.requests,
            "post",
            side_effect=requests.exceptions.Timeout("synthetic timeout"),
        ):
            response = self.post({"message": "Will this time out?", "history": []})
        self.assertEqual(response.status_code, 200)
        self.assertIn("took too long", response.get_data(as_text=True))
        self.assertEqual(self.table_count("rate_events"), 1)
        self.assertEqual(self.table_count("chats"), 0)

    def test_upstream_http_error_streams_safe_message_without_retention(self) -> None:
        with patch.object(
            self.module.requests,
            "post",
            return_value=UpstreamHttpFailure(),
        ):
            response = self.post({"message": "Will this fail?", "history": []})
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("something went wrong", body)
        self.assertNotIn("synthetic upstream", body)
        self.assertEqual(self.table_count("rate_events"), 1)
        self.assertEqual(self.table_count("chats"), 0)

    def test_non_list_history_is_rejected_before_quota(self) -> None:
        response = self.post({"message": "Question", "history": "not-a-list"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.table_count("rate_events"), 0)

    def test_oversized_history_is_rejected_before_quota(self) -> None:
        history = []
        for index in range(3):
            history.extend(
                [
                    {"role": "user", "content": f"question-{index}"},
                    {"role": "assistant", "content": f"answer-{index}"},
                ]
            )
        response = self.post({"message": "Question", "history": history})
        self.assertEqual(response.status_code, 400)
        self.assertIn("too long", response.get_json()["reply"].lower())
        self.assertEqual(self.table_count("rate_events"), 0)

    def test_invalid_role_order_is_rejected_before_quota(self) -> None:
        response = self.post(
            {
                "message": "Question",
                "history": [
                    {"role": "assistant", "content": "answer first"},
                    {"role": "user", "content": "question second"},
                ],
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.table_count("rate_events"), 0)

    def test_request_body_limit_returns_client_error(self) -> None:
        response = self.client.post(
            "/chat",
            data=b"x" * (33 * 1024),
            content_type="application/json",
            environ_base={"REMOTE_ADDR": "172.19.0.10"},
        )
        self.assertIn(response.status_code, {400, 413})
        self.assertEqual(self.table_count("rate_events"), 0)


if __name__ == "__main__":
    unittest.main()