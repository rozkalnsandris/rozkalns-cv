from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from provider_stream import ProviderStreamError, ProviderStreamParser  # noqa: E402


def feed(parser: ProviderStreamParser, event_type: str, payload: dict) -> list:
    self_payload = {"type": event_type, **payload}
    self_event = parser.feed_line(f"event: {event_type}")
    if self_event:
        raise AssertionError("event field must not emit application events")
    return parser.feed_line("data: " + json.dumps(self_payload))


def terminal_response(
    status: str,
    *,
    output_type: str = "message",
    usage: dict | None = None,
    incomplete_reason: str | None = None,
    error=None,
) -> dict:
    response = {
        "status": status,
        "error": error,
        "incomplete_details": (
            {"reason": incomplete_reason} if incomplete_reason else None
        ),
        "output": [{"type": output_type}],
    }
    if usage is not None:
        response["usage"] = usage
    return response


def usage(
    *, input_tokens: object = 12, output_tokens: object = 7, total_tokens: object = 19
) -> dict:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


class ProviderStreamParserTests(unittest.TestCase):
    def test_text_delta_and_completed_usage_are_successful(self) -> None:
        parser = ProviderStreamParser()
        self.assertEqual(feed(parser, "response.created", {}), [])
        event = feed(parser, "response.output_text.delta", {"delta": "Hello"})[0]
        self.assertEqual(event.kind, "content")
        self.assertEqual(event.content, "Hello")
        events = feed(
            parser,
            "response.completed",
            {"response": terminal_response("completed", usage=usage())},
        )
        self.assertEqual([event.kind for event in events], ["terminal", "usage"])
        self.assertEqual(events[0].finish_reason, "stop")
        self.assertEqual(events[1].usage.total_tokens, 19)
        self.assertTrue(parser.done)
        self.assertEqual(parser.finish_reason, "stop")
        parser.finish_eof()

    def test_normal_progress_events_are_ignored(self) -> None:
        parser = ProviderStreamParser()
        for event_type in (
            "response.created",
            "response.queued",
            "response.in_progress",
            "response.output_item.added",
            "response.content_part.added",
            "response.output_text.done",
            "response.content_part.done",
            "response.output_item.done",
            "response.output_text.annotation.added",
            "response.reasoning_summary_part.added",
            "response.reasoning_summary_part.done",
            "response.reasoning_summary_text.delta",
            "response.reasoning_summary_text.done",
            "response.reasoning_text.delta",
            "response.reasoning_text.done",
        ):
            with self.subTest(event_type=event_type):
                self.assertEqual(feed(parser, event_type, {}), [])

    def test_refusal_delta_is_safe_display_text(self) -> None:
        parser = ProviderStreamParser()
        event = feed(parser, "response.refusal.delta", {"delta": "I cannot help."})[0]
        self.assertEqual((event.kind, event.content), ("content", "I cannot help."))
        self.assertEqual(feed(parser, "response.refusal.done", {}), [])

    def test_incomplete_max_output_tokens_maps_to_length(self) -> None:
        parser = ProviderStreamParser()
        events = feed(
            parser,
            "response.incomplete",
            {
                "response": terminal_response(
                    "incomplete",
                    usage=usage(),
                    incomplete_reason="max_output_tokens",
                )
            },
        )
        self.assertEqual(events[0].finish_reason, "length")
        self.assertEqual(parser.usage.total_tokens, 19)
        parser.finish_eof()

    def test_incomplete_content_filter_maps_to_content_filter(self) -> None:
        parser = ProviderStreamParser()
        events = feed(
            parser,
            "response.incomplete",
            {
                "response": terminal_response(
                    "incomplete",
                    usage=usage(),
                    incomplete_reason="content_filter",
                )
            },
        )
        self.assertEqual(events[0].finish_reason, "content_filter")
        parser.finish_eof()

    def test_provider_failed_and_error_are_terminal_failures(self) -> None:
        parser = ProviderStreamParser()
        events = feed(
            parser,
            "response.failed",
            {
                "response": terminal_response(
                    "failed", usage=usage(), error={"code": "provider_error"}
                )
            },
        )
        self.assertEqual(events[0].finish_reason, "provider_failed")
        self.assertEqual(parser.usage.total_tokens, 19)
        parser.finish_eof()

        parser = ProviderStreamParser()
        events = feed(parser, "error", {"code": "server_error"})
        self.assertEqual(events[0].finish_reason, "provider_failed")
        self.assertIsNone(parser.usage)
        parser.finish_eof()

    def test_unexpected_tool_output_fails_as_unsupported_provider_outcome(self) -> None:
        parser = ProviderStreamParser()
        events = feed(
            parser,
            "response.completed",
            {
                "response": terminal_response(
                    "completed", output_type="function_call", usage=usage()
                )
            },
        )
        self.assertEqual(events[0].finish_reason, "tool_calls")
        parser.finish_eof()

    def test_keep_alive_comments_are_ignored(self) -> None:
        parser = ProviderStreamParser()
        self.assertEqual(parser.feed_line(": keep-alive"), [])
        self.assertEqual(parser.feed_line(":keep-alive"), [])

    def test_malformed_json_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line("event: response.output_text.delta")
        with self.assertRaises(ProviderStreamError):
            parser.feed_line("data: {not-json}")

    def test_data_without_event_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            ProviderStreamParser().feed_line(
                'data: {"type":"response.output_text.delta","delta":"x"}'
            )

    def test_event_payload_type_mismatch_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line("event: response.output_text.delta")
        with self.assertRaises(ProviderStreamError):
            parser.feed_line('data: {"type":"response.created"}')

    def test_unknown_event_fails_closed(self) -> None:
        with self.assertRaises(ProviderStreamError):
            feed(ProviderStreamParser(), "response.mystery", {})

    def test_event_without_data_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        parser.feed_line("event: response.output_text.delta")
        with self.assertRaises(ProviderStreamError):
            parser.feed_line("")

    def test_early_eof_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        feed(parser, "response.output_text.delta", {"delta": "partial"})
        with self.assertRaises(ProviderStreamError):
            parser.finish_eof()

    def test_duplicate_terminal_or_late_data_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        feed(
            parser,
            "response.completed",
            {"response": terminal_response("completed", usage=usage())},
        )
        with self.assertRaises(ProviderStreamError):
            parser.feed_line("event: response.completed")

    def test_invalid_usage_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        with self.assertRaises(ProviderStreamError):
            feed(
                parser,
                "response.completed",
                {
                    "response": terminal_response(
                        "completed", usage=usage(total_tokens=None)
                    )
                },
            )

    def test_unexpected_incomplete_reason_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        with self.assertRaises(ProviderStreamError):
            feed(
                parser,
                "response.incomplete",
                {
                    "response": terminal_response(
                        "incomplete",
                        usage=usage(),
                        incomplete_reason="mystery",
                    )
                },
            )

    def test_terminal_status_mismatch_fails_closed(self) -> None:
        parser = ProviderStreamParser()
        with self.assertRaises(ProviderStreamError):
            feed(
                parser,
                "response.completed",
                {"response": terminal_response("failed", usage=usage())},
            )


if __name__ == "__main__":
    unittest.main()
