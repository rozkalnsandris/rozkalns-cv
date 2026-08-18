#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache"}
EXCLUDED_NAMES = {
    ".env.example",
    "cloudflared.env.example",
    "secret-scan.py",
    "PROJECT_KNOWLEDGE.md",
}

PATTERNS = {
    "GitHub classic token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    "OpenAI/OpenRouter-style key": re.compile(r"\bsk-(?:or-v1-)?[A-Za-z0-9_-]{20,}\b"),
    "Telegram bot token": re.compile(r"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "inline tunnel token": re.compile(
        r"(?im)^\s*(?:-\s*)?(?:CF_)?TUNNEL_TOKEN\s*[:=]\s*"
        r"[\"']?(?!\$\{|\{\{|replace|ci-placeholder)([A-Za-z0-9._-]{20,})"
    ),
}

findings: list[str] = []
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if any(part in EXCLUDED_DIRS for part in path.parts):
        continue
    if path.name in EXCLUDED_NAMES:
        continue
    try:
        raw = path.read_bytes()
    except OSError:
        continue
    if b"\x00" in raw[:4096]:
        continue
    text = raw.decode("utf-8", errors="ignore")
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{path.relative_to(ROOT)}:{line}: {label}")

if findings:
    print("SECRET_SCAN=FAIL", file=sys.stderr)
    for row in findings:
        print(row, file=sys.stderr)
    raise SystemExit(1)

print("SECRET_SCAN=PASS")

# Temporary branch-local probe used only to refresh the deterministic content manifest.
def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

profile = json.loads((ROOT / "content" / "profile.json").read_text(encoding="utf-8"))
digest = hashlib.sha256()
digest.update(b"profile\0")
digest.update(canonical_json_bytes(profile))
for language in ("en", "de", "lv"):
    translation = json.loads(
        (ROOT / "content" / "translations" / f"{language}.json").read_text(
            encoding="utf-8"
        )
    )
    digest.update(b"\0translation\0" + language.encode("ascii") + b"\0")
    digest.update(canonical_json_bytes(translation))
print(f"TEMP_CONTENT_SOURCE_SHA256={digest.hexdigest()}")
