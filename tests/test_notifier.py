from __future__ import annotations

import logging
from pathlib import Path
import sys
import time
import unittest
from unittest import mock

import requests

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

import notifier  # noqa: E402


class FakeFuture:
    def __init__(self) -> None:
        self._callbacks = []
        self._done = False

    def add_done_callback(self, callback) -> None:
        if self._done:
            callback(self)
            return
        self._callbacks.append(callback)

    def complete(self) -> None:
        if self._done:
            return
        self._done = True
        callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            callback(self)

    def cancel(self) -> bool:
        if self._done:
            return False
        self.complete()
        return True


class FakeExecutor:
    def __init__(self) -> None:
        self.calls = []
        self.futures: list[FakeFuture] = []
        self.shutdown_calls = []

    def submit(self, fn, *args, **kwargs):
        future = FakeFuture()
        self.calls.append((fn, args, kwargs))
        self.futures.append(future)
        return future

    def shutdown(self, *, wait: bool, cancel_futures: bool) -> None:
        self.shutdown_calls.append((wait, cancel_futures))
        if cancel_futures:
            for future in self.futures:
                future.cancel()


class SuccessfulResponse:
    def raise_for_status(self) -> None:
        return None


class FailingResponse:
    def raise_for_status(self) -> None:
        raise requests.exceptions.HTTPError("telegram failed")


class TelegramNotifierTests(unittest.TestCase):
    @staticmethod
    def _logger():
        logger = logging.getLogger("test-notifier")
        logger.disabled = True
        return logger

    def _wait_until_submit_succeeds(self, active: notifier.TelegramNotifier) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if active.submit("client-2", "second question", "second answer"):
                return
            time.sleep(0.01)
        self.fail("notification capacity was not released")

    def test_redacted_mode_never_queues_raw_content_arguments(self) -> None:
        executor = FakeExecutor()
        with mock.patch.object(notifier, "ThreadPoolExecutor", return_value=executor):
            active = notifier.TelegramNotifier(
                token="token",
                chat_id="chat",
                include_content=False,
                max_pending=2,
                logger=self._logger(),
            )

        question = "PRIVATE QUESTION SENTINEL"
        answer = "PRIVATE ANSWER SENTINEL"
        self.assertTrue(active.submit("client-1", question, answer))
        self.assertEqual(len(executor.calls), 1)
        _fn, args, kwargs = executor.calls[0]
        self.assertEqual(kwargs, {})
        self.assertEqual(args, ("CV assistant interaction\nClient: client-1",))
        self.assertNotIn(question, repr(args))
        self.assertNotIn(answer, repr(args))
        active.close()

    def test_pending_work_is_bounded_and_saturation_drops_without_submit(self) -> None:
        # The permit counts both running and executor-queued notification work.
        executor = FakeExecutor()
        with mock.patch.object(notifier, "ThreadPoolExecutor", return_value=executor):
            active = notifier.TelegramNotifier(
                token="token",
                chat_id="chat",
                include_content=True,
                max_pending=2,
                logger=self._logger(),
            )

        self.assertTrue(active.submit("one", "question-1", "answer-1"))
        self.assertTrue(active.submit("two", "question-2", "answer-2"))
        self.assertFalse(active.submit("three", "question-3", "answer-3"))
        self.assertEqual(len(executor.calls), 2)

        executor.futures[0].complete()
        self.assertTrue(active.submit("three", "question-3", "answer-3"))
        self.assertEqual(len(executor.calls), 3)
        active.close()

    def test_capacity_returns_after_success_and_http_failure(self) -> None:
        for response in (SuccessfulResponse(), FailingResponse()):
            with self.subTest(response=type(response).__name__):
                active = notifier.TelegramNotifier(
                    token="token",
                    chat_id="chat",
                    include_content=False,
                    max_pending=1,
                    logger=self._logger(),
                )
                with mock.patch.object(notifier.requests, "post", return_value=response):
                    self.assertTrue(
                        active.submit("client-1", "first question", "first answer")
                    )
                    self._wait_until_submit_succeeds(active)
                active.close()

    def test_close_cancels_pending_work_releases_permits_and_is_idempotent(self) -> None:
        executor = FakeExecutor()
        with mock.patch.object(notifier, "ThreadPoolExecutor", return_value=executor):
            active = notifier.TelegramNotifier(
                token="token",
                chat_id="chat",
                include_content=False,
                max_pending=2,
                logger=self._logger(),
            )

        self.assertTrue(active.submit("one", "question-1", "answer-1"))
        self.assertTrue(active.submit("two", "question-2", "answer-2"))
        active.close()
        active.close()

        self.assertEqual(executor.shutdown_calls, [(False, True)])
        self.assertFalse(active.submit("three", "question-3", "answer-3"))
        self.assertTrue(active._pending.acquire(blocking=False))
        self.assertTrue(active._pending.acquire(blocking=False))
        self.assertFalse(active._pending.acquire(blocking=False))

    def test_pending_limit_must_be_positive_integer(self) -> None:
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    notifier.TelegramNotifier(
                        token="token",
                        chat_id="chat",
                        include_content=False,
                        max_pending=value,
                        logger=self._logger(),
                    )


if __name__ == "__main__":
    unittest.main()
