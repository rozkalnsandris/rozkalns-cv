#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

NO_DEPLOY = "NO_DEPLOY"
AUTO_DEPLOY_SAFE = "AUTO_DEPLOY_SAFE"
MANUAL_ROLLOUT_REQUIRED = "MANUAL_ROLLOUT_REQUIRED"
DB_HOST_APPLY_REQUIRED = "DB_HOST_APPLY_REQUIRED"

SEVERITY = {
    NO_DEPLOY: 0,
    AUTO_DEPLOY_SAFE: 1,
    MANUAL_ROLLOUT_REQUIRED: 2,
    DB_HOST_APPLY_REQUIRED: 3,
}

NO_DEPLOY_EXACT = frozenset(
    {
        ".gitignore",
        "CONTRIBUTING.md",
        "LICENSE",
        "README.md",
    }
)
NO_DEPLOY_PREFIXES = (
    "docs/",
    "tests/",
    ".github/ISSUE_TEMPLATE/",
)

AUTO_DEPLOY_EXACT = frozenset(
    {
        "frontend-dist-manifest.json",
    }
)
AUTO_DEPLOY_PREFIXES = (
    "content/",
    "frontend/",
    "html/",
    "bot/",
)

MANUAL_EXACT = frozenset(
    {
        "Makefile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "nginx.conf",
        "package.json",
        "package-lock.json",
        "vite.config.mjs",
        "bot/.env.example",
        "bot/Dockerfile",
        "bot/storage.py",
    }
)
MANUAL_PREFIXES = (
    ".github/workflows/",
    "runner/",
    "scripts/",
)

DB_HOST_PREFIXES = (
    "ansible/",
    "host/",
    "infrastructure/",
    "migrations/",
    "ops/host/",
    "ops/systemd/",
    "terraform/",
    "bot/data/",
)

CONTROL_PLANE_PREFIXES = (
    ".github/workflows/",
    "runner/",
)

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ClassifierError(RuntimeError):
    pass


def _normalized(path: str) -> str:
    value = path.replace("\\", "/")
    if not value or value.startswith("/"):
        raise ClassifierError("changed path is empty or absolute")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ClassifierError(f"changed path is unsafe: {path!r}")
    return value


def classify_path(path: str) -> str:
    value = _normalized(path)

    if value.startswith(DB_HOST_PREFIXES):
        return DB_HOST_APPLY_REQUIRED

    if value in MANUAL_EXACT or value.startswith(MANUAL_PREFIXES):
        return MANUAL_ROLLOUT_REQUIRED
    if value.startswith("requirements") or value.startswith("bot/requirements"):
        return MANUAL_ROLLOUT_REQUIRED

    if value in NO_DEPLOY_EXACT or value.startswith(NO_DEPLOY_PREFIXES):
        return NO_DEPLOY

    if value in AUTO_DEPLOY_EXACT or value.startswith(AUTO_DEPLOY_PREFIXES):
        return AUTO_DEPLOY_SAFE

    # Unknown repository paths fail closed toward review. A new runtime or
    # control-plane surface must never silently become auto-deployable.
    return MANUAL_ROLLOUT_REQUIRED


def classify_paths(paths: Iterable[str]) -> dict[str, object]:
    normalized = sorted({_normalized(path) for path in paths})
    per_path = {path: classify_path(path) for path in normalized}
    classification = max(
        per_path.values(),
        key=lambda value: SEVERITY[value],
        default=NO_DEPLOY,
    )
    control_plane_changed = any(
        path.startswith(CONTROL_PLANE_PREFIXES) for path in normalized
    )
    return {
        "classification": classification,
        "control_plane_changed": control_plane_changed,
        "changed_paths": normalized,
        "path_classifications": per_path,
    }


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )
    except FileNotFoundError as exc:
        raise ClassifierError("git is required") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode("utf-8", "replace").strip()
        raise ClassifierError(message or "git command failed") from exc


def changed_paths(repo: Path, base: str, target: str) -> list[str]:
    if not repo.is_dir():
        raise ClassifierError("repository path is missing")
    if not SHA_RE.fullmatch(base) or not SHA_RE.fullmatch(target):
        raise ClassifierError("base and target must be full lowercase commit SHAs")

    for sha in (base, target):
        _git(repo, "cat-file", "-e", f"{sha}^{{commit}}")
    _git(repo, "merge-base", "--is-ancestor", base, target)

    completed = _git(
        repo,
        "diff",
        "--name-only",
        "-z",
        "--diff-filter=ACDMRTUXB",
        base,
        target,
        "--",
    )
    return [
        raw.decode("utf-8", "surrogateescape")
        for raw in completed.stdout.split(b"\0")
        if raw
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify rozkalns-cv production-to-main deploy impact"
    )
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = classify_paths(changed_paths(Path(args.repo), args.base, args.target))
    if args.json:
        json.dump(payload, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
    else:
        print(payload["classification"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClassifierError as exc:
        print(f"DEPLOY_IMPACT_CLASSIFIER=FAIL reason={exc}", file=sys.stderr)
        raise SystemExit(1)
