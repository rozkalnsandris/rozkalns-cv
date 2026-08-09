from __future__ import annotations

from typing import Any, Mapping, Sequence

import requests


class DeepSeekProvider:
    """Narrow HTTP transport boundary for streamed DeepSeek chat completions."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        max_response_tokens: int,
        connect_timeout: float,
        read_timeout: float,
        http: Any = requests,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_response_tokens = max_response_tokens
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._http = http

    def open_stream(self, messages: Sequence[Mapping[str, str]]):
        return self._http.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "messages": list(messages),
                "max_tokens": self._max_response_tokens,
                "temperature": 0.4,
                "thinking": {"type": "disabled"},
                "stream": True,
                "stream_options": {"include_usage": True},
            },
            timeout=(self._connect_timeout, self._read_timeout),
            stream=True,
        )
