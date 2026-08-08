from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from storage import AssistantStore


class MutableClock:
    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class AssistantStoreTests(unittest.TestCase):
    def make_store(
        self,
        directory: str,
        clock: MutableClock,
        *,
        per_client: int = 2,
        global_cap: int = 5,
        retention: int = 7,
        maintenance_sleep: float = 60.0,
    ) -> AssistantStore:
        return AssistantStore(
            Path(directory) / "assistant.sqlite3",
            per_client_hour=per_client,
            daily_global_cap=global_cap,
            chat_retention_days=retention,
            clock=clock,
            maintenance_max_sleep_seconds=maintenance_sleep,
        )

    def test_client_limit_persists_across_store_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            first = self.make_store(tmp, clock, per_client=1)
            self.assertTrue(first.reserve("client-a").allowed)
            second = self.make_store(tmp, clock, per_client=1)
            denied = second.reserve("client-a")
            self.assertFalse(denied.allowed)
            self.assertEqual(denied.reason, "client")
            self.assertGreater(denied.retry_after, 0)

    def test_two_clients_have_independent_buckets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(tmp, clock, per_client=1)
            self.assertTrue(store.reserve("client-a").allowed)
            self.assertTrue(store.reserve("client-b").allowed)
            self.assertFalse(store.reserve("client-a").allowed)

    def test_parallel_reservations_enforce_exact_client_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(
                tmp,
                clock,
                per_client=3,
                global_cap=20,
            )
            with ThreadPoolExecutor(max_workers=8) as pool:
                decisions = list(
                    pool.map(lambda _: store.reserve("client-a"), range(8))
                )
            self.assertEqual(sum(row.allowed for row in decisions), 3)
            self.assertEqual(
                sum(row.reason == "client" for row in decisions), 5
            )
            with sqlite3.connect(store.path) as connection:
                events = connection.execute(
                    "SELECT COUNT(*) FROM rate_events WHERE client_key = ?",
                    ("client-a",),
                ).fetchone()[0]
                global_count = connection.execute(
                    "SELECT request_count FROM daily_usage"
                ).fetchone()[0]
            self.assertEqual(events, 3)
            self.assertEqual(global_count, 3)

    def test_parallel_reservations_enforce_exact_global_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(
                tmp,
                clock,
                per_client=20,
                global_cap=4,
            )
            clients = [f"client-{index}" for index in range(10)]
            with ThreadPoolExecutor(max_workers=10) as pool:
                decisions = list(pool.map(store.reserve, clients))
            self.assertEqual(sum(row.allowed for row in decisions), 4)
            self.assertEqual(
                sum(row.reason == "global" for row in decisions), 6
            )
            with sqlite3.connect(store.path) as connection:
                events = connection.execute(
                    "SELECT COUNT(*) FROM rate_events"
                ).fetchone()[0]
                global_count = connection.execute(
                    "SELECT request_count FROM daily_usage"
                ).fetchone()[0]
            self.assertEqual(events, 4)
            self.assertEqual(global_count, 4)

    def test_global_limit_persists_and_resets_by_utc_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(tmp, clock, global_cap=1)
            self.assertTrue(store.reserve("client-a").allowed)
            denied = store.reserve("client-b")
            self.assertFalse(denied.allowed)
            self.assertEqual(denied.reason, "global")
            clock.value += 86400
            self.assertTrue(store.reserve("client-b").allowed)

    def test_expired_client_events_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(tmp, clock, per_client=1)
            self.assertTrue(store.reserve("client-a").allowed)
            clock.value += 3601
            self.assertTrue(store.reserve("client-a").allowed)

    def test_pseudonym_is_stable_and_does_not_contain_address(self) -> None:
        first = AssistantStore.pseudonymize("203.0.113.10", "secret")
        second = AssistantStore.pseudonymize("203.0.113.10", "secret")
        other = AssistantStore.pseudonymize("203.0.113.11", "secret")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertNotIn("203", first)

    def test_expired_chat_is_removed_without_new_chat_insert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(tmp, clock, retention=2)
            store.record_chat("a", "old", "old-answer")
            clock.value += 2 * 86400
            self.assertEqual(store.purge_expired_chats(), 1)
            with sqlite3.connect(store.path) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM chats"
                ).fetchone()[0]
            self.assertEqual(count, 0)

    def test_startup_purge_applies_current_retention_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            original = self.make_store(tmp, clock, retention=30)
            original.record_chat("a", "old", "answer")
            clock.value += 10 * 86400

            self.make_store(tmp, clock, retention=5)
            with sqlite3.connect(original.path) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM chats"
                ).fetchone()[0]
            self.assertEqual(count, 0)

    def test_background_maintenance_expires_idle_chat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(
                tmp,
                clock,
                retention=1,
                maintenance_sleep=0.01,
            )
            self.addCleanup(store.close)
            store.start_retention_maintenance()
            store.record_chat("a", "question", "answer")
            clock.value += 86400

            deadline = time.monotonic() + 1.0
            count = 1
            while time.monotonic() < deadline:
                with sqlite3.connect(store.path) as connection:
                    count = connection.execute(
                        "SELECT COUNT(*) FROM chats"
                    ).fetchone()[0]
                if count == 0:
                    break
                time.sleep(0.01)
            self.assertEqual(count, 0)

    def test_zero_retention_stores_no_chat_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(tmp, clock, retention=0)
            decision = store.reserve("client-a")
            self.assertTrue(decision.allowed)
            store.record_chat("a", "question", "answer")
            with sqlite3.connect(store.path) as connection:
                chat_count = connection.execute(
                    "SELECT COUNT(*) FROM chats"
                ).fetchone()[0]
                rate_count = connection.execute(
                    "SELECT COUNT(*) FROM rate_events"
                ).fetchone()[0]
                daily_count = connection.execute(
                    "SELECT request_count FROM daily_usage"
                ).fetchone()[0]
            self.assertEqual(chat_count, 0)
            self.assertEqual(rate_count, 1)
            self.assertEqual(daily_count, 1)

    def test_zero_retention_startup_clears_existing_chat_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            original = self.make_store(tmp, clock, retention=7)
            self.assertTrue(original.reserve("client-a").allowed)
            original.record_chat("a", "question", "answer")

            self.make_store(tmp, clock, retention=0)
            with sqlite3.connect(original.path) as connection:
                chat_count = connection.execute(
                    "SELECT COUNT(*) FROM chats"
                ).fetchone()[0]
                rate_count = connection.execute(
                    "SELECT COUNT(*) FROM rate_events"
                ).fetchone()[0]
                daily_count = connection.execute(
                    "SELECT request_count FROM daily_usage"
                ).fetchone()[0]
            self.assertEqual(chat_count, 0)
            self.assertEqual(rate_count, 1)
            self.assertEqual(daily_count, 1)

    def test_manual_purge_supports_all_or_age(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clock = MutableClock(1_700_000_000)
            store = self.make_store(tmp, clock, retention=30)
            store.record_chat("a", "old", "answer")
            clock.value += 10 * 86400
            store.record_chat("b", "new", "answer")
            self.assertEqual(store.purge_chats(older_than_days=5), 1)
            self.assertEqual(store.purge_chats(), 1)


if __name__ == "__main__":
    unittest.main()
