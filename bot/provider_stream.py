from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


_PROGRESS_EVENTS = frozenset(
    {
        "response.created",
        "response.queued",
        "response.in_progress",
        "response.output_item.added",
        "response.content_part.added",
        "response.output_text.done",
        "response.refusal.done",
        "response.content_part.done",
        "response.output_item.done",
        "response.output_text.annotation.added",
        "response.reasoning_summary_part.added",
        "response.reasoning_summary_part.done",
        "response.reasoning_summary_text.delta",
        "response.reasoning_summary_text.done",
        "response.reasoning_text.delta",
        "response.reasoning_text.done",
    }
)
_ALLOWED_OUTPUT_TYPES = frozenset({"message", "reasoning"})


class ProviderStreamError(RuntimeError):
    """Raised when an OpenAI Responses SSE stream violates the locked contract."""


@dataclass(frozen=True)
class ProviderUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ProviderStreamEvent:
    kind: str
    content: str = ""
    finish_reason: str | None = None
    usage: ProviderUsage | None = None


class ProviderStreamParser:
    """Fail-closed parser for the text-only OpenAI Responses stream."""

    def __init__(self) -> None:
        self.finish_reason: str | None = None
        self.done = False
        self.usage: ProviderUsage | None = None
        self._pending_event: str | None = None

    @staticmethod
    def _required_nonnegative_int(value: Any, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ProviderStreamError(f"invalid usage field: {field}")
        return value

    def _parse_usage(self, payload: Any) -> ProviderUsage:
        if not isinstance(payload, dict):
            raise ProviderStreamError("usage must be an object")
        return ProviderUsage(
            prompt_tokens=self._required_nonnegative_int(
                payload.get("input_tokens"), "input_tokens"
            ),
            completion_tokens=self._required_nonnegative_int(
                payload.get("output_tokens"), "output_tokens"
            ),
            total_tokens=self._required_nonnegative_int(
                payload.get("total_tokens"), "total_tokens"
            ),
        )

    @staticmethod
    def _response(payload: dict[str, Any], expected_status: str) -> dict[str, Any]:
        response = payload.get("response")
        if not isinstance(response, dict) or response.get("status") != expected_status:
            raise ProviderStreamError("invalid terminal response")
        return response

    @staticmethod
    def _has_unsupported_output(response: dict[str, Any]) -> bool:
        output = response.get("output")
        if not isinstance(output, list):
            raise ProviderStreamError("terminal response output must be a list")
        for item in output:
            if not isinstance(item, dict):
                raise ProviderStreamError("terminal response output item must be an object")
            if item.get("type") not in _ALLOWED_OUTPUT_TYPES:
                return True
        return False

    def _terminal(
        self,
        finish_reason: str,
        *,
        usage: ProviderUsage | None,
    ) -> list[ProviderStreamEvent]:
        if self.done or self.finish_reason is not None:
            raise ProviderStreamError("duplicate terminal event")
        self.finish_reason = finish_reason
        self.done = True
        self.usage = usage
        events = [
            ProviderStreamEvent(kind="terminal", finish_reason=finish_reason)
        ]
        if usage is not None:
            events.append(ProviderStreamEvent(kind="usage", usage=usage))
        return events

    def _handle_payload(
        self, event_name: str, payload: dict[str, Any]
    ) -> list[ProviderStreamEvent]:
        if self.done:
            raise ProviderStreamError("event received after terminal response")

        if event_name in {"response.output_text.delta", "response.refusal.delta"}:
            delta = payload.get("delta")
            if not isinstance(delta, str):
                raise ProviderStreamError("output delta must be text")
            return [ProviderStreamEvent(kind="content", content=delta)] if delta else []

        if event_name in _PROGRESS_EVENTS:
            return []

        if event_name == "response.completed":
            response = self._response(payload, "completed")
            if response.get("error") is not None or response.get("incomplete_details") is not None:
                raise ProviderStreamError("completed response carries failure metadata")
            usage = self._parse_usage(response.get("usage"))
            if self._has_unsupported_output(response):
                return self._terminal("tool_calls", usage=usage)
            return self._terminal("stop", usage=usage)

        if event_name == "response.incomplete":
            response = self._response(payload, "incomplete")
            details = response.get("incomplete_details")
            if not isinstance(details, dict):
                raise ProviderStreamError("incomplete response lacks details")
            reason = details.get("reason")
            reason_map = {
                "max_output_tokens": "length",
                "content_filter": "content_filter",
            }
            if reason not in reason_map:
                raise ProviderStreamError("unexpected incomplete reason")
            usage = self._parse_usage(response.get("usage"))
            if self._has_unsupported_output(response):
                return self._terminal("tool_calls", usage=usage)
            return self._terminal(reason_map[reason], usage=usage)

        if event_name == "response.failed":
            response = self._response(payload, "failed")
            usage_payload = response.get("usage")
            usage = self._parse_usage(usage_payload) if usage_payload is not None else None
            return self._terminal("provider_failed", usage=usage)

        if event_name == "error":
            return self._terminal("provider_failed", usage=None)

        raise ProviderStreamError("unexpected Responses event type")

    def feed_line(self, line: str) -> list[ProviderStreamEvent]:
        if not isinstance(line, str):
            raise ProviderStreamError("provider stream line must be text")

        if not line:
            if self._pending_event is not None:
                raise ProviderStreamError("SSE event ended without data")
            return []

        if line.startswith(":"):
            return []

        if line.startswith("event:"):
            if self.done:
                raise ProviderStreamError("event received after terminal response")
            if self._pending_event is not None:
                raise ProviderStreamError("duplicate SSE event field")
            event_name = line[6:].strip()
            if not event_name:
                raise ProviderStreamError("empty SSE event name")
            self._pending_event = event_name
            return []

        if not line.startswith("data:"):
            raise ProviderStreamError("unexpected SSE field")
        if self._pending_event is None:
            raise ProviderStreamError("SSE data received without event field")

        raw = line[5:].strip()
        if not raw:
            raise ProviderStreamError("empty SSE data")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProviderStreamError("malformed provider JSON") from error
        if not isinstance(payload, dict):
            raise ProviderStreamError("Responses event payload must be an object")

        event_name = self._pending_event
        self._pending_event = None
        if payload.get("type") != event_name:
            raise ProviderStreamError("SSE event name does not match payload type")
        return self._handle_payload(event_name, payload)

    def finish_eof(self) -> None:
        if self._pending_event is not None:
            raise ProviderStreamError("provider stream ended mid-event")
        if not self.done or self.finish_reason is None:
            raise ProviderStreamError("provider stream ended before terminal response")
