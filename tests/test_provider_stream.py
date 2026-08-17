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


def usage_chunk(
    *,
    prompt_tokens: object = 12,
    completion_tokens: object = 7,
    total_tokens: object = 19,
) -> str:
    import json

    return "data: " + json.dumps(
        {
            "object": "chat.completion.chunk",
            "choices": [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }
    )


class ProviderStreamParserTests(unittest.TestCase):
    def test_harmless_empty_delta_is_allowed(self) -> None:
        parser = ProviderStreamParser()
        self.assertEqual(parser.feed_line(chunk("")), [])

    def test_stop_usage_done_is_complete(self) -> None:
        parser = ProviderStreamParser()
        events = parser.feed_line(chunk("Hello"))
        self.assertEqual(events[0].kind, "content")
        terminal = parser.feed_line(chunk("", finish_reason="stop"))
        self.assertEqual(terminal[0].finish_reason, "stop")
        usage = parser.feed_line(usage_chunk())[0]
        self.assertEqual(usage.kind, "usage")
        parser.feed_line("data: [DONE]")
        parser.finish_eof()
        self.assertTrue(parser.done)
        self.assertEqual(parser.usage.total_tokens, 19)

    def test_documented_keep_alive_comments_are_ignored_across_stream_states(self) -> None:
        parser = ProviderStreamParser()
        self.assertEqual(parser.feed_line(": keep-alive"), [])
        self.assertEqual(parser.feed_line(":keep-alive"), [])

        events = parser.feed_line(chunk("Hello"))
        self.assertEqual(events[0].kind, "content")
        self.assertEqual(parser.feed_line(": keep-alive"), [])

        terminal = parser.feed_line(chunk("", finish_reason="stop"))
        self.assertEqual(terminal[0].finish_reason, "stop")
        self.assertEqual(parser.feed_line(": keep-alive"), [])

        usage = parser.feed_line(usage_chunk())[0]
        self.assertEqual(usage.kind, "usage")
        self.assertEqual(parser.feed_line(": keep-alive"), [])

        parser.feed_line("data: [DONE]")
        parser.finish_eof()
        self.assertTrue(parser.done)
        self.assertEqual(parser.finish_reason, "stop")
        self.assertEqual(parser.usage.total_tokens, 19)

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

    def test_usage_only_chunk_after_terminal_is_accepted(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line(chunk("", finish_reason="stop"))
        event = parser.feed_line(usage_chunk())[0]
        self.assertEqual(event.kind, "usage")
        self.assertEqual(event.usage.total_tokens, 19)

    def test_malformed_json_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line("data: {not-json}")

    def test_non_data_sse_field_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line("event: message")

    def test_arbitrary_non_comment_line_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line("keep-alive")

    def test_invalid_choice_shape_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line('data: {"choices": [{}, {}]}')

    def test_unexpected_terminal_reason_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line(chunk("", finish_reason="mystery"))

    def test_done_without_terminal_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line("data: [DONE]")

    def test_done_without_usage_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line(chunk("", finish_reason="stop"))
        with self.assertRaises(ProviderStreamError):
            parser.feed_line("data: [DONE]")

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

    def test_usage_before_terminal_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line(usage_chunk())

    def test_usage_on_normal_choice_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        with self.assertRaises(ProviderStreamError):
            parser.feed_line(
                chunk(
                    "Hello",
                    usage={
                        "prompt_tokens": 12,
                        "completion_tokens": 1,
                        "total_tokens": 13,
                    },
                )
            )

    def test_content_after_terminal_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line(chunk("", finish_reason="stop"))
        with self.assertRaises(ProviderStreamError):
            parser.feed_line(chunk("late content"))

    def test_duplicate_usage_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line(chunk("", finish_reason="stop"))
        parser.feed_line(usage_chunk())
        with self.assertRaises(ProviderStreamError):
            parser.feed_line(usage_chunk())

    def test_malformed_usage_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line(chunk("", finish_reason="stop"))
        with self.assertRaises(ProviderStreamError):
            parser.feed_line(usage_chunk(total_tokens=None))


if __name__ == "__main__":
    unittest.main()
