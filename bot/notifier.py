from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging

import requests


class TelegramNotifier:
    def __init__(
        self,
        *,
        token: str,
        chat_id: str,
        include_content: bool,
        max_workers: int = 1,
        logger: logging.Logger | None = None,
    ) -> None:
        self._token = token
        self._chat_id = chat_id
        self._include_content = include_content
        self._logger = logger or logging.getLogger(__name__)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="cvbot-notify",
        )
        self._closed = False

    @property
    def configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def submit(self, client_key: str, question: str, answer: str) -> None:
        if self._closed or not self.configured:
            return
        try:
            self._executor.submit(self._send, client_key, question, answer)
        except RuntimeError:
            return

    def _send(self, client_key: str, question: str, answer: str) -> None:
        try:
            text = f"CV assistant interaction\nClient: {client_key}"
            if self._include_content:
                text += f"\n\nQuestion: {question[:300]}\n\nAnswer: {answer[:600]}"
            response = requests.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                data={"chat_id": self._chat_id, "text": text},
                timeout=10,
            )
            response.raise_for_status()
        except Exception as error:
            self._logger.error(
                "telegram notification failed: %s", type(error).__name__
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
