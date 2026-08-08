from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
from pathlib import Path
import sqlite3
import threading
import time
from typing import Callable


LOGGER = logging.getLogger(__name__)

CLIENT_KEY_SECRET_MIN_BYTES = 32
_CLIENT_KEY_SECRET_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


class ClientKeySecretError(RuntimeError):
    """Raised when the dedicated pseudonymization key is unsafe to use."""


def validate_client_key_secret(value: str, provider_key: str = "") -> str:
    """Validate a dedicated URL-safe HMAC key without exposing its value."""

    if not isinstance(value, str) or not value:
        raise ClientKeySecretError("CLIENT_KEY_SECRET is required")
    if not value.isascii() or any(
        character not in _CLIENT_KEY_SECRET_ALPHABET for character in value
    ):
        raise ClientKeySecretError("CLIENT_KEY_SECRET has invalid format")
    padding = "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(
            value + padding, altchars=b"-_", validate=True
        )
    except (binascii.Error, ValueError) as error:
        raise ClientKeySecretError(
            "CLIENT_KEY_SECRET has invalid format"
        ) from error
    if len(decoded) < CLIENT_KEY_SECRET_MIN_BYTES:
        raise ClientKeySecretError("CLIENT_KEY_SECRET is too short")
    if provider_key and hmac.compare_digest(value, provider_key):
        raise ClientKeySecretError(
            "CLIENT_KEY_SECRET must be dedicated to pseudonymization"
        )
    return value


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    reason: str | None
    retry_after: int
    client_remaining: int
    global_remaining: int


class AssistantStore:
    """Durable rate limits and privacy-bounded chat telemetry in SQLite."""

    def __init__(
        self,
        path: str | Path,
        *,
        per_client_hour: int,
        daily_global_cap: int,
        chat_retention_days: int,
        clock: Callable[[], float] = time.time,
        maintenance_max_sleep_seconds: float = 60.0,
    ) -> None:
        if per_client_hour <= 0 or daily_global_cap <= 0:
            raise ValueError("rate limits must be positive")
        if chat_retention_days < 0:
            raise ValueError("chat retention days cannot be negative")
        if maintenance_max_sleep_seconds <= 0:
            raise ValueError("maintenance sleep must be positive")
        self.path = Path(path)
        self.per_client_hour = per_client_hour
        self.daily_global_cap = daily_global_cap
        self.chat_retention_days = chat_retention_days
        self.clock = clock
        self.maintenance_max_sleep_seconds = float(
            maintenance_max_sleep_seconds
        )
        self._maintenance_stop = threading.Event()
        self._maintenance_wake = threading.Event()
        self._maintenance_thread: threading.Thread | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        # Startup maintenance makes a restart enforce the current retention
        # policy before any new chat succeeds. A zero-day policy removes raw
        # chat content immediately while leaving durable quota tables intact.
        self.purge_expired_chats()

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
        """Persist raw chat text only when retention is explicitly nonzero."""

        if self.chat_retention_days == 0:
            return
        now = float(self.clock())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO chats(
                    occurred_at, client_key, question, answer
                ) VALUES (?, ?, ?, ?)
                """,
                (now, client_key, question, answer),
            )
            connection.execute("COMMIT")
        # Recompute the next expiry promptly instead of waiting for an
        # unrelated request or for the maximum maintenance sleep to elapse.
        self._maintenance_wake.set()

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
                    "DELETE FROM chats WHERE occurred_at <= ?", (cutoff,)
                )
            connection.execute("COMMIT")
            return max(0, cursor.rowcount)

    def purge_expired_chats(self) -> int:
        """Apply the configured raw-content retention policy immediately."""

        if self.chat_retention_days == 0:
            return self.purge_chats()
        return self.purge_chats(older_than_days=self.chat_retention_days)

    def _seconds_until_next_chat_expiry(self) -> float | None:
        if self.chat_retention_days == 0:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT MIN(occurred_at) FROM chats"
            ).fetchone()
        if not row or row[0] is None:
            return None
        expires_at = float(row[0]) + (self.chat_retention_days * 86400)
        return max(0.0, expires_at - float(self.clock()))

    def _retention_maintenance_loop(self) -> None:
        while not self._maintenance_stop.is_set():
            try:
                self.purge_expired_chats()
                until_expiry = self._seconds_until_next_chat_expiry()
            except Exception as error:
                # Never include row content or DB payloads in maintenance logs.
                LOGGER.error(
                    "chat retention maintenance failed: %s",
                    type(error).__name__,
                )
                until_expiry = None

            sleep_for = self.maintenance_max_sleep_seconds
            if until_expiry is not None:
                sleep_for = min(sleep_for, max(0.01, until_expiry))
            self._maintenance_wake.wait(sleep_for)
            self._maintenance_wake.clear()

    def start_retention_maintenance(self) -> None:
        """Start one idempotent janitor for nonzero raw-chat retention."""

        if self.chat_retention_days == 0:
            return
        if self._maintenance_thread and self._maintenance_thread.is_alive():
            return
        self._maintenance_stop.clear()
        self._maintenance_thread = threading.Thread(
            target=self._retention_maintenance_loop,
            name="cvbot-chat-retention",
            daemon=True,
        )
        self._maintenance_thread.start()

    def close(self, *, timeout: float = 2.0) -> None:
        """Stop the retention janitor without touching durable quota state."""

        self._maintenance_stop.set()
        self._maintenance_wake.set()
        thread = self._maintenance_thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        self._maintenance_thread = None
