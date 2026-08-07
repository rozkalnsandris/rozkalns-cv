#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

INPUTS = (
    "bot/Dockerfile",
    "bot/requirements.lock",
    "bot/app.py",
    "bot/contact.py",
    "bot/storage.py",
    "docker-compose.yml",
    "security/supply-chain.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--explain", action="store_true")
    return parser.parse_args()


def calculate(root: Path) -> tuple[str, list[tuple[str, str]]]:
    digest = hashlib.sha256()
    rows: list[tuple[str, str]] = []
    for relative in INPUTS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"required build input is missing: {relative}")
        content = path.read_bytes()
        file_digest = hashlib.sha256(content).hexdigest()
        rows.append((relative, file_digest))
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest(), rows


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    try:
        build_id, rows = calculate(root)
    except (OSError, ValueError) as error:
        print(f"BUILD_INPUT_ID=FAIL ERROR={error}", file=sys.stderr)
        return 1
    if args.explain:
        for relative, file_digest in rows:
            print(f"INPUT {file_digest}  {relative}")
    print(build_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
