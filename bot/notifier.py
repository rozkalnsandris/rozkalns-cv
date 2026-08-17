from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging
from threading import BoundedSemaphore, Lock

import requests


DEFAULT_MAX_PENDING = 8


class TelegramNotifier:
    def __init__(
        self,
        *,
        token: str,
        chat_id: str,
        include_content: bool,
        max_workers: int = 1,
        max_pending: int = DEFAULT_MAX_PENDING,
        logger: logging.Logger | None = None,
    ) -> None:
        if not isinstance(max_pending, int) or isinstance(max_pending, bool) or max_pending < 1:
            raise ValueError("max_pending must be a positive integer")
        self._token = token
        self._chat_id = chat_id
        self._include_content = include_content
        self._logger = logger or logging.getLogger(__name__)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="cvbot-notify",
        )
        self._pending = BoundedSemaphore(max_pending)
        self._state_lock = Lock()
        self._closed = False

    @property
    def configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def submit(self, client_key: str, question: str, answer: str) -> bool:
        if not self.configured:
            return False
        with self._state_lock:
            if self._closed or not self._pending.acquire(blocking=False):
                return False
            text = self._message_text(client_key, question, answer)
            try:
                future = self._executor.submit(self._send_text, text)
            except RuntimeError:
                self._pending.release()
                return False
            future.add_done_callback(self._release_pending)
            return True

    def _message_text(self, client_key: str, question: str, answer: str) -> str:
        text = f"CV assistant interaction\nClient: {client_key}"
        if self._include_content:
            text += f"\n\nQuestion: {question[:300]}\n\nAnswer: {answer[:600]}"
        return text

    def _release_pending(self, _future: Future[object]) -> None:
        self._pending.release()

    def _send_text(self, text: str) -> None:
        try:
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
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            executor = self._executor
        executor.shutdown(wait=False, cancel_futures=True)
