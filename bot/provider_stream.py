from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


ALLOWED_FINISH_REASONS = frozenset(
    {
        "stop",
        "length",
        "content_filter",
        "tool_calls",
        "insufficient_system_resource",
    }
)

_STATE_ACTIVE = "ACTIVE"
_STATE_TERMINAL = "TERMINAL"
_STATE_USAGE = "USAGE"
_STATE_DONE = "DONE"


class ProviderStreamError(RuntimeError):
    """Raised when the DeepSeek SSE stream violates the documented contract."""


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
    """Fail-closed parser for DeepSeek include_usage chat streams."""

    def __init__(self) -> None:
        self.finish_reason: str | None = None
        self.done = False
        self.usage: ProviderUsage | None = None
        self._state = _STATE_ACTIVE

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
                payload.get("prompt_tokens"), "prompt_tokens"
            ),
            completion_tokens=self._required_nonnegative_int(
                payload.get("completion_tokens"), "completion_tokens"
            ),
            total_tokens=self._required_nonnegative_int(
                payload.get("total_tokens"), "total_tokens"
            ),
        )

    def feed_line(self, line: str) -> list[ProviderStreamEvent]:
        if self.done:
            if line:
                raise ProviderStreamError("data received after [DONE]")
            return []
        if not line:
            return []
        if not line.startswith("data:"):
            raise ProviderStreamError("unexpected non-data SSE field")

        raw = line[5:].strip()
        if not raw:
            raise ProviderStreamError("empty data event")
        if raw == "[DONE]":
            if self._state != _STATE_USAGE:
                if self.finish_reason is None:
                    raise ProviderStreamError(
                        "[DONE] received before terminal finish_reason"
                    )
                raise ProviderStreamError("[DONE] received before usage chunk")
            self.done = True
            self._state = _STATE_DONE
            return [ProviderStreamEvent(kind="done")]

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProviderStreamError("malformed provider JSON") from error
        if not isinstance(payload, dict):
            raise ProviderStreamError("provider chunk must be an object")
        if payload.get("object") not in {None, "chat.completion.chunk"}:
            raise ProviderStreamError("unexpected provider object type")

        choices = payload.get("choices")
        usage_payload = payload.get("usage")

        if choices == []:
            if self._state == _STATE_ACTIVE:
                raise ProviderStreamError("usage chunk received before terminal")
            if self._state == _STATE_USAGE:
                raise ProviderStreamError("duplicate usage chunk")
            if self._state != _STATE_TERMINAL:
                raise ProviderStreamError("usage chunk received in invalid state")
            if usage_payload is None:
                raise ProviderStreamError("empty choices without usage")
            usage = self._parse_usage(usage_payload)
            self.usage = usage
            self._state = _STATE_USAGE
            return [ProviderStreamEvent(kind="usage", usage=usage)]

        if self._state != _STATE_ACTIVE:
            raise ProviderStreamError("choice chunk received after terminal")

        if not isinstance(choices, list) or len(choices) != 1:
            raise ProviderStreamError("provider chunk must contain one choice")
        if usage_payload is not None:
            raise ProviderStreamError("ordinary choice chunk must have null usage")

        choice = choices[0]
        if not isinstance(choice, dict) or choice.get("index") not in {None, 0}:
            raise ProviderStreamError("invalid provider choice")

        delta = choice.get("delta")
        if not isinstance(delta, dict):
            raise ProviderStreamError("provider delta must be an object")
        content = delta.get("content")
        if content is not None and not isinstance(content, str):
            raise ProviderStreamError("provider content must be text or null")

        events: list[ProviderStreamEvent] = []
        if content:
            events.append(ProviderStreamEvent(kind="content", content=content))

        finish_reason = choice.get("finish_reason")
        if finish_reason is not None:
            if not isinstance(finish_reason, str):
                raise ProviderStreamError("finish_reason must be text or null")
            if finish_reason not in ALLOWED_FINISH_REASONS:
                raise ProviderStreamError("unexpected finish_reason")
            self.finish_reason = finish_reason
            self._state = _STATE_TERMINAL
            events.append(
                ProviderStreamEvent(
                    kind="terminal",
                    finish_reason=finish_reason,
                )
            )

        return events

    def finish_eof(self) -> None:
        if not self.done:
            raise ProviderStreamError("provider stream ended before [DONE]")
        if self.finish_reason is None:
            raise ProviderStreamError("provider stream ended without finish_reason")
        if self.usage is None:
            raise ProviderStreamError("provider stream ended without usage")
