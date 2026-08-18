#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ANALYZER_CHECKS = (
    "Analyze (actions)",
    "Analyze (python)",
    "Analyze (javascript-typescript)",
)
META_CHECK = "CodeQL"
REQUIRED_CHECKS = ANALYZER_CHECKS + (META_CHECK,)
_ALLOWED_STATUSES = {
    "queued",
    "in_progress",
    "completed",
    "requested",
    "waiting",
    "pending",
}


class EvidenceError(RuntimeError):
    pass


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{label} must be non-empty text")
    return value.strip()


def _safe_rows(payload: Any) -> list[tuple[str, str, str | None, str]]:
    if not isinstance(payload, dict):
        raise EvidenceError("Checks API response must be an object")
    check_runs = payload.get("check_runs")
    if not isinstance(check_runs, list):
        raise EvidenceError("Checks API response check_runs must be a list")

    rows: list[tuple[str, str, str | None, str]] = []
    for index, item in enumerate(check_runs):
        if not isinstance(item, dict):
            raise EvidenceError(f"check_runs[{index}] must be an object")
        name = _require_text(item.get("name"), f"check_runs[{index}].name")
        status = _require_text(item.get("status"), f"check_runs[{index}].status")
        if status not in _ALLOWED_STATUSES:
            raise EvidenceError(f"check_runs[{index}].status is unsupported")
        conclusion = item.get("conclusion")
        if conclusion is not None and not isinstance(conclusion, str):
            raise EvidenceError(f"check_runs[{index}].conclusion must be text or null")
        app = item.get("app")
        if app is None:
            app_slug = "unknown"
        elif isinstance(app, dict):
            slug = app.get("slug")
            app_slug = slug.strip() if isinstance(slug, str) and slug.strip() else "unknown"
        else:
            raise EvidenceError(f"check_runs[{index}].app must be an object or null")
        rows.append((name, status, conclusion, app_slug))
    return rows


def _one_required(
    rows: list[tuple[str, str, str | None, str]], name: str
) -> tuple[str, str, str | None, str] | None:
    matches = [row for row in rows if row[0] == name]
    if not matches:
        return None
    if len(matches) != 1:
        raise EvidenceError(f"duplicate required check: {name}")
    return matches[0]


def evaluate_check_runs(payload: Any) -> tuple[bool, tuple[str, ...]]:
    rows = _safe_rows(payload)
    pending: list[str] = []

    for required in ANALYZER_CHECKS:
        match = _one_required(rows, required)
        if match is None:
            pending.append(f"missing:{required}")
            continue

        _name, status, conclusion, _app_slug = match
        if status != "completed":
            pending.append(f"pending:{required}:{status}")
            continue
        if conclusion != "success":
            raise EvidenceError(
                f"required analyzer did not succeed: {required}: {conclusion!r}"
            )

    meta = _one_required(rows, META_CHECK)
    if meta is None:
        pending.append(f"missing:{META_CHECK}")
    else:
        _name, status, conclusion, _app_slug = meta
        if status != "completed":
            pending.append(f"pending:{META_CHECK}:{status}")
        elif conclusion == "neutral":
            # GitHub may publish a transient neutral PR CodeQL meta-check while
            # the default-setup analyzer checks are still finishing. A later
            # latest check replaces it with the final success/failure verdict.
            # Wait boundedly; neutral is never accepted as PASS.
            pending.append(f"pending:{META_CHECK}:neutral")
        elif conclusion != "success":
            raise EvidenceError(
                f"required meta-check did not succeed: {META_CHECK}: {conclusion!r}"
            )

    return not pending, tuple(pending)


def fetch_check_runs(repository: str, sha: str, token: str) -> dict[str, Any]:
    if not REPOSITORY_RE.fullmatch(repository):
        raise EvidenceError("repository must use owner/name form")
    if not SHA_RE.fullmatch(sha):
        raise EvidenceError("sha must be a lowercase 40-character commit SHA")
    if not token:
        raise EvidenceError("GITHUB_TOKEN is required")

    owner, name = repository.split("/", 1)
    url = (
        "https://api.github.com/repos/"
        f"{quote(owner, safe='')}/{quote(name, safe='')}/commits/{sha}/check-runs"
        "?per_page=100&filter=latest"
    )
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "rozkalns-cv-codeql-evidence",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read()
    except HTTPError as error:
        raise EvidenceError(f"Checks API HTTP {error.code}") from error
    except URLError as error:
        raise EvidenceError("Checks API transport failure") from error
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise EvidenceError("Checks API returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise EvidenceError("Checks API response must be an object")
    return payload


def print_safe_observed(payload: Any) -> None:
    rows = _safe_rows(payload)
    interesting = [
        row
        for row in rows
        if row[0] in REQUIRED_CHECKS
        or row[0].lower().startswith("analyze (")
        or "codeql" in row[0].lower()
    ]
    if not interesting:
        print("CODEQL_OBSERVED=none")
        return
    for name, status, conclusion, app_slug in sorted(interesting):
        print(
            "CODEQL_OBSERVED="
            f"name={name!r} status={status!r} conclusion={conclusion!r} "
            f"app={app_slug!r}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--delay-seconds", type=float, default=5.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.attempts <= 60:
        print("CODEQL_EVIDENCE=FAIL ERROR=attempts must be between 1 and 60", file=sys.stderr)
        return 1
    if not 0 <= args.delay_seconds <= 30:
        print(
            "CODEQL_EVIDENCE=FAIL ERROR=delay-seconds must be between 0 and 30",
            file=sys.stderr,
        )
        return 1

    token = os.environ.get("GITHUB_TOKEN", "")
    last_pending: tuple[str, ...] = ()

    for attempt in range(1, args.attempts + 1):
        try:
            payload = fetch_check_runs(args.repository, args.sha, token)
            complete, pending = evaluate_check_runs(payload)
        except EvidenceError as error:
            print(f"CODEQL_EVIDENCE=FAIL ERROR={error}", file=sys.stderr)
            return 1

        print(f"CODEQL_EVIDENCE_ATTEMPT={attempt}/{args.attempts}")
        print_safe_observed(payload)
        if complete:
            print(f"CODEQL_EVIDENCE_SHA={args.sha}")
            print("CODEQL_EVIDENCE=PASS")
            return 0

        last_pending = pending
        print("CODEQL_EVIDENCE_WAIT=" + ",".join(pending))
        if attempt < args.attempts:
            time.sleep(args.delay_seconds)

    print(
        "CODEQL_EVIDENCE=FAIL ERROR=timeout waiting for required checks: "
        + ",".join(last_pending),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
