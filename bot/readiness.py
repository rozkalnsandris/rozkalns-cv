from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    reason: str | None = None


def check_local_readiness(
    db_path: str | Path,
    *,
    llm_api_key: str,
    client_key_secret: str,
    llm_model: str,
    supported_models: frozenset[str],
) -> ReadinessResult:
    """Verify local chat prerequisites without calling external providers."""

    if not llm_api_key:
        return ReadinessResult(False, "config")
    if not client_key_secret:
        return ReadinessResult(False, "config")
    if llm_model not in supported_models:
        return ReadinessResult(False, "config")

    path = Path(db_path)
    try:
        connection = sqlite3.connect(path, timeout=2, isolation_level=None)
        try:
            connection.execute("PRAGMA busy_timeout = 2000")
            row = connection.execute("PRAGMA quick_check(1)").fetchone()
            if not row or row[0] != "ok":
                return ReadinessResult(False, "storage")

            # BEGIN IMMEDIATE proves the persistent SQLite path can acquire a
            # write transaction. The schema probe is rolled back, so readiness
            # leaves no application row or schema mutation behind.
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS __cvbot_readiness_probe (id INTEGER)"
            )
            connection.execute("ROLLBACK")
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return ReadinessResult(False, "storage")

    return ReadinessResult(True)
