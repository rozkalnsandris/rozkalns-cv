from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from pathlib import Path
import sqlite3
import time
from typing import Callable


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    reason: str | None
    retry_after: int
    client_remaining: int
    global_remaining: int


class AssistantStore:
    """Durable rate limits and bounded chat telemetry in one SQLite file."""

    def __init__(
        self,
        path: str | Path,
        *,
        per_client_hour: int,
        daily_global_cap: int,
        chat_retention_days: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if per_client_hour <= 0 or daily_global_cap <= 0:
            raise ValueError("rate limits must be positive")
        if chat_retention_days < 0:
            raise ValueError("chat retention days cannot be negative")
        self.path = Path(path)
        self.per_client_hour = per_client_hour
        self.daily_global_cap = daily_global_cap
        self.chat_retention_days = chat_retention_days
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10,
            isolation_level=None,
        )
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rate_events (
                    client_key TEXT NOT NULL,
                    occurred_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rate_events_client_time
                    ON rate_events(client_key, occurred_at);

                CREATE TABLE IF NOT EXISTS daily_usage (
                    usage_day TEXT PRIMARY KEY,
                    request_count INTEGER NOT NULL
                        CHECK(request_count >= 0)
                );

                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at REAL NOT NULL,
                    client_key TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chats_occurred_at
                    ON chats(occurred_at);
                """
            )

    @staticmethod
    def pseudonymize(address: str, secret: str) -> str:
        if not secret:
            raise ValueError("client key secret is required")
        digest = hmac.new(
            secret.encode("utf-8"),
            address.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest[:24]

    @staticmethod
    def _utc_day(now: float) -> str:
        return datetime.fromtimestamp(now, timezone.utc).date().isoformat()

    @staticmethod
    def _seconds_until_next_utc_day(now: float) -> int:
        current = datetime.fromtimestamp(now, timezone.utc)
        tomorrow = datetime.combine(
            current.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        return max(1, int((tomorrow - current).total_seconds()))

    def reserve(self, client_key: str) -> RateDecision:
        """Atomically reserve one validated upstream attempt.

        Accepted provider attempts consume quota even when the provider later
        times out or returns an error. Invalid HTTP payloads must be rejected
        before this function is called.
        """

        now = float(self.clock())
        cutoff = now - 3600
        usage_day = self._utc_day(now)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM rate_events WHERE occurred_at <= ?", (cutoff,)
            )
            connection.execute(
                "DELETE FROM daily_usage WHERE usage_day < ?", (usage_day,)
            )

            global_row = connection.execute(
                "SELECT request_count FROM daily_usage WHERE usage_day = ?",
                (usage_day,),
            ).fetchone()
            global_count = int(global_row[0]) if global_row else 0
            if global_count >= self.daily_global_cap:
                connection.execute("ROLLBACK")
                return RateDecision(
                    allowed=False,
                    reason="global",
                    retry_after=self._seconds_until_next_utc_day(now),
                    client_remaining=0,
                    global_remaining=0,
                )

            client_row = connection.execute(
                """
                SELECT COUNT(*), MIN(occurred_at)
                FROM rate_events
                WHERE client_key = ? AND occurred_at > ?
                """,
                (client_key, cutoff),
            ).fetchone()
            client_count = int(client_row[0])
            oldest = float(client_row[1]) if client_row[1] is not None else now
            if client_count >= self.per_client_hour:
                connection.execute("ROLLBACK")
                return RateDecision(
                    allowed=False,
                    reason="client",
                    retry_after=max(1, int(oldest + 3600 - now)),
                    client_remaining=0,
                    global_remaining=max(
                        0, self.daily_global_cap - global_count
                    ),
                )

            connection.execute(
                "INSERT INTO rate_events(client_key, occurred_at) VALUES (?, ?)",
                (client_key, now),
            )
            connection.execute(
                """
                INSERT INTO daily_usage(usage_day, request_count)
                VALUES (?, 1)
                ON CONFLICT(usage_day) DO UPDATE SET
                    request_count = request_count + 1
                """,
                (usage_day,),
            )
            connection.execute("COMMIT")
            return RateDecision(
                allowed=True,
                reason=None,
                retry_after=0,
                client_remaining=max(
                    0, self.per_client_hour - client_count - 1
                ),
                global_remaining=max(
                    0, self.daily_global_cap - global_count - 1
                ),
            )
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    def record_chat(
        self,
        client_key: str,
        question: str,
        answer: str,
    ) -> None:
        now = float(self.clock())
        cutoff = now - (self.chat_retention_days * 86400)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if self.chat_retention_days == 0:
                connection.execute("DELETE FROM chats")
            else:
                connection.execute(
                    "DELETE FROM chats WHERE occurred_at < ?", (cutoff,)
                )
                connection.execute(
                    """
                    INSERT INTO chats(
                        occurred_at, client_key, question, answer
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (now, client_key, question, answer),
                )
            connection.execute("COMMIT")

    def purge_chats(self, *, older_than_days: int | None = None) -> int:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if older_than_days is None:
                cursor = connection.execute("DELETE FROM chats")
            else:
                if older_than_days < 0:
                    raise ValueError("older_than_days cannot be negative")
                cutoff = float(self.clock()) - (older_than_days * 86400)
                cursor = connection.execute(
                    "DELETE FROM chats WHERE occurred_at < ?", (cutoff,)
                )
            connection.execute("COMMIT")
            return max(0, cursor.rowcount)
