from __future__ import annotations

from typing import Mapping, Sequence

import requests


class OpenAIResponsesProvider:
    """Narrow HTTP transport boundary for streamed OpenAI Responses."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        max_response_tokens: int,
        connect_timeout: float,
        read_timeout: float,
        http=requests,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_response_tokens = max_response_tokens
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._http = http

    def open_stream(
        self,
        *,
        instructions: str,
        input_items: Sequence[Mapping[str, str]],
        safety_identifier: str,
    ):
        return self._http.post(
            f"{self._base_url}/v1/responses",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            json={
                "model": self._model,
                "instructions": instructions,
                "input": list(input_items),
                "max_output_tokens": self._max_response_tokens,
                "reasoning": {"effort": "none"},
                "text": {"verbosity": "low"},
                "store": False,
                "stream": True,
                "tools": [],
                "truncation": "disabled",
                "safety_identifier": safety_identifier,
            },
            timeout=(self._connect_timeout, self._read_timeout),
            stream=True,
        )
