from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from provider_stream import (  # noqa: E402
    ProviderStreamError,
    ProviderStreamParser,
)


def chunk(
    content: str | None = "",
    *,
    finish_reason: str | None = None,
    usage: dict | None = None,
) -> str:
    import json

    payload = {
        "object": "chat.completion.chunk",
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage,
    }
    return "data: " + json.dumps(payload)


class ProviderStreamParserTests(unittest.TestCase):
    def test_harmless_empty_delta_is_allowed(self) -> None:
        parser = ProviderStreamParser()
        self.assertEqual(parser.feed_line(chunk("")), [])

    def test_stop_then_done_is_complete(self) -> None:
        parser = ProviderStreamParser()
        events = parser.feed_line(chunk("Hello"))
        self.assertEqual(events[0].kind, "content")
        terminal = parser.feed_line(chunk("", finish_reason="stop"))
        self.assertEqual(terminal[0].finish_reason, "stop")
        parser.feed_line("data: [DONE]")
        parser.finish_eof()
        self.assertTrue(parser.done)

    def test_all_documented_terminal_reasons_are_classified(self) -> None:
        for reason in (
            "stop",
            "length",
            "content_filter",
            "tool_calls",
            "insufficient_system_resource",
        ):
            with self.subTest(reason=reason):
                parser = ProviderStreamParser()
                events = parser.feed_line(chunk("", finish_reason=reason))
                self.assertEqual(events[0].finish_reason, reason)

    def test_usage_only_chunk_is_accepted(self) -> None:
        import json

        parser = ProviderStreamParser()
        line = "data: " + json.dumps(
            {
                "object": "chat.completion.chunk",
                "choices": [],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 7,
                    "total_tokens": 19,
                },
            }
        )
        event = parser.feed_line(line)[0]
        self.assertEqual(event.kind, "usage")
        self.assertEqual(event.usage.total_tokens, 19)

    def test_malformed_json_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line("data: {not-json}")

    def test_non_data_sse_field_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line("event: message")

    def test_invalid_choice_shape_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line('data: {"choices": [{}, {}]}')

    def test_unexpected_terminal_reason_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line(chunk("", finish_reason="mystery"))

    def test_done_without_terminal_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line("data: [DONE]")

    def test_early_eof_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line(chunk("partial"))
        with self.assertRaises(ProviderStreamError):
            parser.finish_eof()

    def test_duplicate_terminal_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line(chunk("", finish_reason="stop"))
        with self.assertRaises(ProviderStreamError):
            parser.feed_line(chunk("", finish_reason="length"))


if __name__ == "__main__":
    unittest.main()
