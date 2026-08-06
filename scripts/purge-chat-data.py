#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from storage import AssistantStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete retained CV assistant conversation content."
    )
    parser.add_argument(
        "--db",
        default=os.getenv(
            "ASSISTANT_DB_PATH",
            "/home/andris/docker/cv/bot/data/assistant.sqlite3",
        ),
        help="SQLite database path",
    )
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=None,
        help="Delete only conversations older than this many days",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = AssistantStore(
        args.db,
        per_client_hour=1,
        daily_global_cap=1,
        chat_retention_days=7,
    )
    deleted = store.purge_chats(older_than_days=args.older_than_days)
    print(f"CHAT_ROWS_DELETED={deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
