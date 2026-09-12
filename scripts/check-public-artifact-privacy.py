#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "security" / "public-artifact-privacy.json"
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<![\w+])\+\d(?:[\s().-]*\d){6,14}(?!\d)")
PHONE_URI_RE = re.compile(r"(?i)(?:tel:|sms:|https?://(?:wa\.me|api\.whatsapp\.com)/)\s*\+?\d")
STREET_SUFFIX = r"(?:street|st\.?|road|rd\.?|avenue|ave\.?|straße|strasse|str\.?|weg|allee|iela|gatve|prospekts)"
STREET_NUMBER_FIRST_RE = re.compile(
    rf"(?i)\b\d{{1,5}}[A-Za-z]?\s+(?:[A-Za-zÀ-ž][A-Za-zÀ-ž.'-]*\s+){{1,5}}{STREET_SUFFIX}\b"
)
STREET_NUMBER_LAST_RE = re.compile(rf"(?i)\b{STREET_SUFFIX}\s+\d{{1,5}}[A-Za-z]?\b")
CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|token|password)\b[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}"
)
CREDENTIAL_TOKEN_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


@dataclass(frozen=True, order=True)
class Finding:
    artifact: str
    rule: str


class ScanError(RuntimeError):
    def __init__(self, artifact: str, rule: str) -> None:
        super().__init__(rule)
        self.artifact = artifact
        self.rule = rule


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScanError(path.name, "invalid_policy") from error
    if policy.get("schema_version") != 1:
        raise ScanError(path.name, "unsupported_policy_schema")
    if policy.get("ADDRESS_PUBLICATION_AUTHORIZED") is not False:
        raise ScanError(path.name, "address_publication_must_remain_false")
    for key in ("artifact_root", "text_extensions", "pdf_extensions", "allowed_public_emails", "private_only_markers"):
        if key not in policy:
            raise ScanError(path.name, f"missing_policy_{key}")
    return policy


def scan_text(artifact: str, text: str, policy: dict[str, Any]) -> list[Finding]:
    rules: set[str] = set()
    allowed_emails = {str(value).casefold() for value in policy["allowed_public_emails"]}
    if any(match.group(0).casefold() not in allowed_emails for match in EMAIL_RE.finditer(text)):
        rules.add("unexpected_email")
    if PHONE_RE.search(text) or PHONE_URI_RE.search(text):
        rules.add("protected_phone")
    if STREET_NUMBER_FIRST_RE.search(text) or STREET_NUMBER_LAST_RE.search(text):
        rules.add("street_address")
    if CREDENTIAL_ASSIGNMENT_RE.search(text) or CREDENTIAL_TOKEN_RE.search(text) or PRIVATE_KEY_RE.search(text):
        rules.add("credential_material")
    if any(str(marker) in text for marker in policy["private_only_markers"]):
        rules.add("private_fixture_marker")
    return [Finding(artifact, rule) for rule in sorted(rules)]


def extract_pdf_text(root: Path, path: Path, artifact: str) -> str:
    tool = shutil.which("pdftotext")
    if tool is None:
        raise ScanError(artifact, "pdf_text_extractor_unavailable")
    try:
        result = subprocess.run(
            [tool, "-layout", str(path), "-"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ScanError(artifact, "pdf_text_extraction_failed") from error
    return result.stdout


def discover_artifacts(root: Path, policy: dict[str, Any]) -> list[Path]:
    artifact_root = root / str(policy["artifact_root"])
    if not artifact_root.is_dir():
        raise ScanError(str(policy["artifact_root"]), "artifact_root_missing")
    suffixes = {str(value).lower() for value in (*policy["text_extensions"], *policy["pdf_extensions"])}
    return sorted(path for path in artifact_root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def scan_repository(root: Path, policy: dict[str, Any]) -> tuple[list[str], list[Finding]]:
    root = root.resolve()
    text_extensions = {str(value).lower() for value in policy["text_extensions"]}
    pdf_extensions = {str(value).lower() for value in policy["pdf_extensions"]}
    artifacts: list[str] = []
    findings: set[Finding] = set()
    for path in discover_artifacts(root, policy):
        artifact = path.relative_to(root).as_posix()
        artifacts.append(artifact)
        if path.suffix.lower() in text_extensions:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise ScanError(artifact, "text_artifact_unreadable") from error
        elif path.suffix.lower() in pdf_extensions:
            text = extract_pdf_text(root, path, artifact)
        else:
            continue
        findings.update(scan_text(artifact, text, policy))
    if not artifacts:
        raise ScanError(str(policy["artifact_root"]), "no_public_artifacts")
    return artifacts, sorted(findings)


def format_findings(findings: list[Finding]) -> str:
    return "\n".join(
        f"PUBLIC_ARTIFACT_PRIVACY=FAIL artifact={finding.artifact} rule={finding.rule}"
        for finding in sorted(findings)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=str(ROOT))
    parser.add_argument("--policy")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    policy_path = Path(args.policy).resolve() if args.policy else root / "security" / "public-artifact-privacy.json"
    try:
        policy = load_policy(policy_path)
        artifacts, findings = scan_repository(root, policy)
    except ScanError as error:
        print(f"PUBLIC_ARTIFACT_PRIVACY=FAIL artifact={error.artifact} rule={error.rule}", file=sys.stderr)
        return 1
    if findings:
        print(format_findings(findings), file=sys.stderr)
        return 1
    print(f"PUBLIC_ARTIFACT_PRIVACY_ARTIFACTS={len(artifacts)}")
    print("PUBLIC_ARTIFACT_PRIVACY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
