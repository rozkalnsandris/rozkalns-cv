from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from provider import DeepSeekProvider  # noqa: E402


class FakeHttp:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return object()


class ProviderTransportTests(unittest.TestCase):
    def test_stream_request_matches_locked_v4_contract(self) -> None:
        http = FakeHttp()
        provider = DeepSeekProvider(
            base_url="https://api.deepseek.com/",
            api_key="test-key",
            model="deepseek-v4-flash",
            max_response_tokens=350,
            connect_timeout=5,
            read_timeout=70,
            http=http,
        )
        result = provider.open_stream(
            [{"role": "user", "content": "hello"}]
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(http.calls), 1)
        call = http.calls[0]
        self.assertEqual(call["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(call["timeout"], (5, 70))
        self.assertTrue(call["stream"])
        self.assertEqual(call["json"]["model"], "deepseek-v4-flash")
        self.assertEqual(call["json"]["thinking"], {"type": "disabled"})
        self.assertEqual(call["json"]["stream_options"], {"include_usage": True})
        self.assertEqual(
            call["json"]["messages"],
            [{"role": "user", "content": "hello"}],
        )
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-key")


if __name__ == "__main__":
    unittest.main()
