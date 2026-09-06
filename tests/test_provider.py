from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from provider import OpenAIResponsesProvider  # noqa: E402


class FakeHttp:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return object()


class ProviderTransportTests(unittest.TestCase):
    def test_stream_request_matches_locked_responses_contract(self) -> None:
        http = FakeHttp()
        provider = OpenAIResponsesProvider(
            base_url="https://api.openai.com/",
            api_key="test-key",
            model="gpt-5.6-luna",
            max_response_tokens=350,
            connect_timeout=5,
            read_timeout=70,
            http=http,
        )
        result = provider.open_stream(
            instructions="CV-only system prompt",
            input_items=[{"role": "user", "content": "hello"}],
            safety_identifier="abc123pseudonym",
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(http.calls), 1)
        call = http.calls[0]
        self.assertEqual(call["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(call["timeout"], (5, 70))
        self.assertTrue(call["stream"])
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(call["headers"]["Accept"], "text/event-stream")

        payload = call["json"]
        self.assertEqual(payload["model"], "gpt-5.6-luna")
        self.assertEqual(payload["instructions"], "CV-only system prompt")
        self.assertEqual(
            payload["input"], [{"role": "user", "content": "hello"}]
        )
        self.assertEqual(payload["max_output_tokens"], 350)
        self.assertEqual(payload["reasoning"], {"effort": "none"})
        self.assertEqual(payload["text"], {"verbosity": "low"})
        self.assertIs(payload["store"], False)
        self.assertIs(payload["stream"], True)
        self.assertEqual(payload["tools"], [])
        self.assertEqual(payload["truncation"], "disabled")
        self.assertEqual(payload["safety_identifier"], "abc123pseudonym")
        for forbidden in (
            "previous_response_id",
            "conversation",
            "temperature",
        ):
            self.assertNotIn(forbidden, payload)


if __name__ == "__main__":
    unittest.main()
