#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

EXPECTED_PERMISSIONS = {
    "browser-lab.yml": {"contents": "read"},
    "ci.yml": {"contents": "read"},
    "codeql-evidence.yml": {"contents": "read", "checks": "read"},
    "github-only-policy-drift.yml": {"contents": "read"},
    "pdf-quality.yml": {"contents": "read"},
}
REUSABLE_JOB_ALLOWLIST = {
    ("github-only-policy-drift.yml", "github-only-policy-drift"),
}
REUSABLE_WORKFLOW_PIN = re.compile(
    r"^rozkalnsandris/ops-workflows/\.github/workflows/"
    r"[A-Za-z0-9_.-]+\.ya?ml@([0-9a-f]{40})$"
)
MAX_TIMEOUT_MINUTES = 60


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _mapping(lines: list[str], section: str, child_indent: int) -> dict[str, str]:
    start = next(
        (index for index, line in enumerate(lines) if line == f"{section}:"),
        None,
    )
    if start is None:
        raise ValueError(f"missing top-level {section}: mapping")
    values: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent(line)
        if indent < child_indent:
            break
        if indent != child_indent:
            continue
        key, separator, value = line.strip().partition(":")
        if not separator or not value.strip():
            raise ValueError(f"{section}.{key} must be an explicit scalar")
        values[key] = value.strip().strip("'\"")
    return values


def _jobs(lines: list[str]) -> dict[str, dict[str, str]]:
    try:
        start = lines.index("jobs:")
    except ValueError as exc:
        raise ValueError("missing top-level jobs: mapping") from exc
    jobs: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent(line)
        if indent == 0:
            break
        stripped = line.strip()
        if indent == 2 and stripped.endswith(":"):
            current = stripped[:-1]
            jobs[current] = {}
            continue
        if current is None or indent != 4:
            continue
        key, separator, value = stripped.partition(":")
        if separator and value.strip():
            jobs[current][key] = value.strip().strip("'\"")
    if not jobs:
        raise ValueError("workflow must define at least one job")
    return jobs


def validate_workflow_text(filename: str, text: str) -> None:
    expected = EXPECTED_PERMISSIONS.get(filename)
    if expected is None:
        raise ValueError(f"workflow lacks explicit permission policy: {filename}")
    lines = text.splitlines()
    actual = _mapping(lines, "permissions", 2)
    if actual != expected:
        raise ValueError(
            f"{filename}: permissions must be exactly {expected}, got {actual}"
        )

    for job_name, job in _jobs(lines).items():
        runs_on = job.get("runs-on")
        reusable = job.get("uses")
        if runs_on:
            if reusable:
                raise ValueError(f"{filename}:{job_name}: job mixes runs-on and uses")
            raw_timeout = job.get("timeout-minutes")
            if raw_timeout is None:
                raise ValueError(f"{filename}:{job_name}: missing timeout-minutes")
            try:
                timeout = int(raw_timeout)
            except ValueError as exc:
                raise ValueError(
                    f"{filename}:{job_name}: timeout-minutes must be an integer"
                ) from exc
            if not 1 <= timeout <= MAX_TIMEOUT_MINUTES:
                raise ValueError(
                    f"{filename}:{job_name}: timeout-minutes must be 1..{MAX_TIMEOUT_MINUTES}"
                )
            continue

        if reusable:
            if (filename, job_name) not in REUSABLE_JOB_ALLOWLIST:
                raise ValueError(
                    f"{filename}:{job_name}: reusable job is not explicitly allowlisted"
                )
            if not REUSABLE_WORKFLOW_PIN.fullmatch(reusable):
                raise ValueError(
                    f"{filename}:{job_name}: reusable workflow must use an immutable 40-hex pin"
                )
            continue

        raise ValueError(
            f"{filename}:{job_name}: job must be local runs-on or an allowlisted reusable call"
        )


def validate_repository(root: Path) -> None:
    workflow_dir = root / ".github" / "workflows"
    paths = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))
    names = {path.name for path in paths}
    expected_names = set(EXPECTED_PERMISSIONS)
    if names != expected_names:
        raise ValueError(
            "workflow inventory must match explicit policy: "
            f"expected={sorted(expected_names)} actual={sorted(names)}"
        )
    for path in paths:
        validate_workflow_text(path.name, path.read_text(encoding="utf-8"))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    try:
        validate_repository(root)
    except ValueError as exc:
        print(f"WORKFLOW_SECURITY_CONTRACT=FAIL: {exc}", file=sys.stderr)
        return 1
    print("WORKFLOW_SECURITY_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
