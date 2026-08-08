#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "de", "lv")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MONTH_RE = re.compile(r"^[0-9]{4}-[0-9]{2}$")
PARTIAL_DATE_RE = re.compile(r"^[0-9]{4}(?:-[0-9]{2})?$")
VERSION_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\.[1-9][0-9]*$")


class ContentError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContentError(f"invalid JSON: {path.relative_to(ROOT)}") from error


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def require_object(value: Any, label: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContentError(f"{label} must be an object")
    if set(value) != keys:
        raise ContentError(f"{label} fields do not match the schema")
    return value


def require_text(value: Any, label: str, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise ContentError(f"{label} must be non-empty text")
    return value.strip()


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContentError(f"{label} must be a non-empty list")
    items = [require_text(item, f"{label} item") for item in value]
    if len(set(items)) != len(items):
        raise ContentError(f"{label} contains duplicate values")
    return items


def require_unique_ids(rows: list[Any], label: str) -> None:
    identifiers: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ContentError(f"{label}[{index}] must be an object")
        identifier = require_text(row.get("id"), f"{label}[{index}].id")
        if not ID_RE.fullmatch(identifier):
            raise ContentError(f"{label}[{index}].id is invalid")
        identifiers.append(identifier)
    if len(set(identifiers)) != len(identifiers):
        raise ContentError(f"{label} contains duplicate ids")


def validate_profile(profile: Any) -> dict[str, Any]:
    root_keys = {
        "schema_version",
        "content_version",
        "identity",
        "contact",
        "languages",
        "experience",
        "education",
        "skills",
        "projects",
        "infrastructure",
    }
    profile = require_object(profile, "profile", root_keys)
    if profile["schema_version"] != 2:
        raise ContentError("profile.schema_version must be 2")
    version = require_text(profile["content_version"], "profile.content_version")
    if not VERSION_RE.fullmatch(version):
        raise ContentError("profile.content_version is invalid")

    identity = require_object(
        profile["identity"],
        "profile.identity",
        {"name", "role", "location", "availability", "career_goal"},
    )
    for key in ("name", "role", "location"):
        require_text(identity[key], f"profile.identity.{key}", 2)
    require_text(identity["career_goal"], "profile.identity.career_goal", 10)
    availability = require_text(
        identity["availability"], "profile.identity.availability"
    )
    if not MONTH_RE.fullmatch(availability):
        raise ContentError("profile.identity.availability is invalid")

    contact = require_object(
        profile["contact"],
        "profile.contact",
        {"email", "phone", "github", "website"},
    )
    email = require_object(
        contact["email"], "profile.contact.email", {"value", "visibility"}
    )
    require_text(email["value"], "profile.contact.email.value", 3)
    if email["visibility"] != "public":
        raise ContentError("profile.contact.email must be public")
    phone = require_object(
        contact["phone"], "profile.contact.phone", {"visibility"}
    )
    if phone["visibility"] != "runtime-protected":
        raise ContentError("profile.contact.phone must be runtime-protected")
    for key in ("github", "website"):
        entry = require_object(
            contact[key], f"profile.contact.{key}", {"value", "visibility"}
        )
        require_text(entry["value"], f"profile.contact.{key}.value", 2)
        if entry["visibility"] != "public":
            raise ContentError(f"profile.contact.{key} must be public")

    languages = profile["languages"]
    if not isinstance(languages, list) or not languages:
        raise ContentError("profile.languages must be a non-empty list")
    language_names: list[str] = []
    for index, item in enumerate(languages):
        item = require_object(
            item, f"profile.languages[{index}]", {"name", "level"}
        )
        language_names.append(
            require_text(item["name"], f"profile.languages[{index}].name", 2)
        )
        require_text(item["level"], f"profile.languages[{index}].level")
    if len(set(language_names)) != len(language_names):
        raise ContentError("profile.languages contains duplicate names")

    experience = profile["experience"]
    if not isinstance(experience, list) or not experience:
        raise ContentError("profile.experience must be a non-empty list")
    require_unique_ids(experience, "profile.experience")
    for index, item in enumerate(experience):
        allowed = {
            "id",
            "role",
            "organization",
            "location",
            "start",
            "end",
            "highlights",
            "end_planned",
        }
        required = allowed - {"end_planned"}
        if not isinstance(item, dict) or not required.issubset(item) or not set(item).issubset(allowed):
            raise ContentError(f"profile.experience[{index}] fields are invalid")
        for key in ("role", "organization", "location"):
            require_text(item[key], f"profile.experience[{index}].{key}", 2)
        for key in ("start", "end"):
            if not PARTIAL_DATE_RE.fullmatch(
                require_text(item[key], f"profile.experience[{index}].{key}")
            ):
                raise ContentError(f"profile.experience[{index}].{key} is invalid")
        require_string_list(
            item["highlights"], f"profile.experience[{index}].highlights"
        )
        if "end_planned" in item and not isinstance(item["end_planned"], bool):
            raise ContentError(
                f"profile.experience[{index}].end_planned must be boolean"
            )

    education = profile["education"]
    if not isinstance(education, list) or not education:
        raise ContentError("profile.education must be a non-empty list")
    require_unique_ids(education, "profile.education")
    education_allowed = {
        "id",
        "title",
        "organization",
        "start",
        "end",
        "status",
        "detail",
    }
    for index, item in enumerate(education):
        if not isinstance(item, dict) or "title" not in item or not set(item).issubset(education_allowed):
            raise ContentError(f"profile.education[{index}] fields are invalid")
        require_text(item["title"], f"profile.education[{index}].title", 2)
        for key in ("organization", "status", "detail"):
            if key in item:
                require_text(item[key], f"profile.education[{index}].{key}", 2)
        for key in ("start", "end"):
            if key in item and not re.fullmatch(
                r"[0-9]{4}",
                require_text(item[key], f"profile.education[{index}].{key}"),
            ):
                raise ContentError(f"profile.education[{index}].{key} is invalid")

    skills = require_object(
        profile["skills"],
        "profile.skills",
        {"core", "working", "learning", "foundations"},
    )
    for key, value in skills.items():
        require_string_list(value, f"profile.skills.{key}")

    projects = profile["projects"]
    if not isinstance(projects, list) or not projects:
        raise ContentError("profile.projects must be a non-empty list")
    require_unique_ids(projects, "profile.projects")
    for index, item in enumerate(projects):
        item = require_object(
            item,
            f"profile.projects[{index}]",
            {"id", "title", "facts"},
        )
        require_text(item["title"], f"profile.projects[{index}].title", 2)
        require_string_list(item["facts"], f"profile.projects[{index}].facts")

    infrastructure = require_object(
        profile["infrastructure"],
        "profile.infrastructure",
        {"host", "storage", "runtime", "availability", "public_site"},
    )
    for key, value in infrastructure.items():
        require_text(value, f"profile.infrastructure.{key}", 2)

    return profile


def load_translations() -> tuple[dict[str, dict[str, str]], dict[str, bytes]]:
    parsed: dict[str, dict[str, str]] = {}
    raw: dict[str, bytes] = {}
    reference_keys: set[str] | None = None
    for language in LANGUAGES:
        path = ROOT / "content" / "translations" / f"{language}.json"
        try:
            content = path.read_bytes()
            value = json.loads(content)
        except (OSError, json.JSONDecodeError) as error:
            raise ContentError(
                f"invalid translation: {path.relative_to(ROOT)}"
            ) from error
        if not isinstance(value, dict) or not value:
            raise ContentError(f"translation {language} must be an object")
        if any(not isinstance(key, str) or not isinstance(text, str) or not text.strip() for key, text in value.items()):
            raise ContentError(f"translation {language} contains invalid values")
        keys = set(value)
        if reference_keys is None:
            reference_keys = keys
        elif keys != reference_keys:
            raise ContentError(f"translation key mismatch for {language}")
        parsed[language] = value
        raw[language] = content
    return parsed, raw


def source_digest(profile: dict[str, Any], translations: dict[str, dict[str, str]]) -> str:
    digest = hashlib.sha256()
    digest.update(b"profile\0")
    digest.update(canonical_json_bytes(profile))
    for language in LANGUAGES:
        digest.update(b"\0translation\0" + language.encode("ascii") + b"\0")
        digest.update(canonical_json_bytes(translations[language]))
    return digest.hexdigest()


def build_system_prompt(profile: dict[str, Any]) -> str:
    identity = profile["identity"]
    contact = profile["contact"]
    lines = [
        f"You are the CV assistant for {identity['name']}.",
        "Answer only questions about this public CV, professional skills, projects, experience, education, and availability.",
        "",
        "PUBLIC PROFILE",
        f"Name: {identity['name']}",
        f"Role: {identity['role']}",
        f"Location: {identity['location']}",
        f"Availability: {identity['availability']}",
        f"Career goal: {identity['career_goal']}",
        "",
        "PUBLIC CONTACT",
        f"Email: {contact['email']['value']}",
        "Phone and WhatsApp: available only through the verified contact section on the public CV.",
        f"GitHub: {contact['github']['value']}",
        f"Website: {contact['website']['value']}",
        "",
        "LANGUAGES",
    ]
    lines.extend(
        f"- {item['name']}: {item['level']}" for item in profile["languages"]
    )
    lines.extend(["", "WORK EXPERIENCE"])
    for item in profile["experience"]:
        planned = " planned" if item.get("end_planned") else ""
        lines.append(
            f"- {item['role']} — {item['organization']} · {item['location']} "
            f"({item['start']} – {item['end']}{planned})"
        )
        lines.extend(f"  - {highlight}" for highlight in item["highlights"])
    lines.extend(["", "EDUCATION"])
    for item in profile["education"]:
        detail: list[str] = []
        if item.get("organization"):
            detail.append(item["organization"])
        if item.get("start") or item.get("end"):
            detail.append(f"{item.get('start', '?')} – {item.get('end', '?')}")
        if item.get("status"):
            detail.append(item["status"])
        if item.get("detail"):
            detail.append(item["detail"])
        suffix = f" — {'; '.join(detail)}" if detail else ""
        lines.append(f"- {item['title']}{suffix}")
    lines.extend(["", "TECHNICAL SKILLS"])
    skill_labels = {
        "core": "Core",
        "working": "Working knowledge",
        "learning": "Learning",
        "foundations": "Foundations",
    }
    for key in ("core", "working", "learning", "foundations"):
        lines.append(f"- {skill_labels[key]}: {', '.join(profile['skills'][key])}")
    lines.extend(["", "PROJECTS"])
    for item in profile["projects"]:
        lines.append(f"- {item['title']}: {'; '.join(item['facts'])}")
    lines.extend(["", "INFRASTRUCTURE"])
    for key, value in profile["infrastructure"].items():
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    lines.extend(
        [
            "",
            "RULES",
            "- Do not answer unrelated questions.",
            "- The dedicated recruiting email is public and may be provided directly.",
            "- Do not reveal, infer, or guess the protected phone number; direct phone or WhatsApp requests to the verified contact section on the public CV.",
            "- For salary expectations, say Andris is open to discussion based on the role and company.",
            f"- For the start date, say Andris is available from {identity['availability']}.",
            "- Keep answers concise, factual, and professional.",
            "",
        ]
    )
    return "\n".join(lines)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)



def expected_pdf_manifest(content_sha256: str) -> dict[str, Any]:
    pdf_paths = {
        "en": ROOT / "html" / "cv.pdf",
        "de": ROOT / "html" / "cv-de.pdf",
        "lv": ROOT / "html" / "cv-lv.pdf",
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "source_sha256": content_sha256,
        "pdfs": {},
    }
    for language, path in pdf_paths.items():
        if not path.is_file() or path.stat().st_size == 0:
            raise ContentError(f"PDF is missing: {path.relative_to(ROOT)}")
        result["pdfs"][language] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": file_sha256(path),
        }
    return result


def render_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def assert_bytes(path: Path, expected: bytes) -> None:
    try:
        actual = path.read_bytes()
    except OSError as error:
        raise ContentError(f"generated file is missing: {path.relative_to(ROOT)}") from error
    if actual != expected:
        raise ContentError(f"generated file is stale: {path.relative_to(ROOT)}")


def check_or_write(args: argparse.Namespace) -> None:
    profile = validate_profile(load_json(ROOT / "content" / "profile.json"))
    translations, _raw_translations = load_translations()
    content_sha256 = source_digest(profile, translations)
    prompt_bytes = build_system_prompt(profile).encode("utf-8")

    expected_files: dict[Path, bytes] = {
        ROOT / "bot" / "system_prompt.txt": prompt_bytes,
    }

    pdf_manifest_path = ROOT / "content" / "pdf-manifest.json"
    if args.accept_pdfs:
        if not args.write:
            raise ContentError("--accept-pdfs requires --write")
        expected_files[pdf_manifest_path] = render_json(
            expected_pdf_manifest(content_sha256)
        )
    else:
        manifest = load_json(pdf_manifest_path)
        expected_manifest = expected_pdf_manifest(content_sha256)
        if manifest != expected_manifest:
            raise ContentError(
                "PDF manifest is stale; regenerate and visually review PDFs before accepting them"
            )
        expected_files[pdf_manifest_path] = render_json(expected_manifest)

    if args.write:
        for path, content in expected_files.items():
            atomic_write(path, content)
    else:
        for path, content in expected_files.items():
            assert_bytes(path, content)

    print(f"CONTENT_SOURCE_SHA256={content_sha256}")
    print("CONTENT_BUILD=PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument(
        "--accept-pdfs",
        action="store_true",
        help="record current PDF hashes for the current canonical source after visual review",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        check_or_write(args)
    except ContentError as error:
        print(f"CONTENT_BUILD=FAIL ERROR={error}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
