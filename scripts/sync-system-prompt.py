#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "bot" / "app.py"
PROMPT_PATH = ROOT / "bot" / "system_prompt.txt"
HEADER = "# ---------------- GENERATED KNOWLEDGE (do not edit) ----------------"
BEGIN = "# BEGIN GENERATED SYSTEM PROMPT"
END = "# END GENERATED SYSTEM PROMPT"
OLD_BLOCK = re.compile(
    r"# ---------------- KNOWLEDGE \(CV facts only\) ----------------\n"
    r"SYSTEM_PROMPT = \"\"\".*?\"\"\"\n",
    re.DOTALL,
)
GENERATED_BLOCK = re.compile(
    re.escape(HEADER)
    + r"\n"
    + re.escape(BEGIN)
    + r"\nSYSTEM_PROMPT = \"\"\".*?\"\"\"\n"
    + re.escape(END),
    re.DOTALL,
)


class PromptSyncError(RuntimeError):
    pass


def atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def expected_app_text(app_text: str, prompt: str) -> str:
    if '"""' in prompt:
        raise PromptSyncError("generated prompt contains a triple quote")
    prompt = prompt.rstrip("\n")
    block = (
        f"{HEADER}\n"
        f"{BEGIN}\n"
        f'SYSTEM_PROMPT = """{prompt}"""\n'
        f"{END}"
    )
    if BEGIN in app_text or END in app_text:
        if app_text.count(BEGIN) != 1 or app_text.count(END) != 1:
            raise PromptSyncError("generated prompt markers are malformed")
        updated, count = GENERATED_BLOCK.subn(block, app_text, count=1)
    else:
        updated, count = OLD_BLOCK.subn(block, app_text, count=1)
    if count != 1:
        raise PromptSyncError("system prompt block was not found exactly once")
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        app_text = APP_PATH.read_text(encoding="utf-8")
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        expected = expected_app_text(app_text, prompt)
        if args.write:
            atomic_write(APP_PATH, expected)
        elif app_text != expected:
            raise PromptSyncError("bot/app.py contains a stale generated prompt")
    except (OSError, PromptSyncError) as error:
        print(f"PROMPT_SYNC=FAIL ERROR={error}", file=os.sys.stderr)
        return 1
    print("PROMPT_SYNC=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
