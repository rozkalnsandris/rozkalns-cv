from __future__ import annotations

from threading import BoundedSemaphore, Lock


class ProviderStreamLease:
    """One idempotently releasable provider-stream capacity lease."""

    __slots__ = ("_semaphore", "_lock", "_released")

    def __init__(self, semaphore: BoundedSemaphore) -> None:
        self._semaphore = semaphore
        self._lock = Lock()
        self._released = False

    def release(self) -> bool:
        with self._lock:
            if self._released:
                return False
            self._semaphore.release()
            self._released = True
            return True


class ProviderStreamCapacity:
    """Non-blocking bounded admission for synchronous provider streams."""

    __slots__ = ("limit", "_semaphore")

    def __init__(self, limit: int) -> None:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("provider stream limit must be a positive integer")
        self.limit = limit
        self._semaphore = BoundedSemaphore(limit)

    def try_acquire(self) -> ProviderStreamLease | None:
        if not self._semaphore.acquire(blocking=False):
            return None
        return ProviderStreamLease(self._semaphore)
