#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "de", "lv")
DEFAULT_PROJECTS = ("p1", "p3", "p2")
DEVOPS_CORE_ORDER = (1, 2, 10, 3, 0, 7, 8, 4, 5, 6, 9)
LINUX_CORE_ORDER = (0, 9, 3, 4, 5, 6, 1, 2, 7, 8, 10)
PDF_CASES = {
    "en": {"language": "en", "path": ROOT / "html" / "cv.pdf", "variant": None, "projects": DEFAULT_PROJECTS, "core_order": None},
    "de": {"language": "de", "path": ROOT / "html" / "cv-de.pdf", "variant": None, "projects": DEFAULT_PROJECTS, "core_order": None},
    "lv": {"language": "lv", "path": ROOT / "html" / "cv-lv.pdf", "variant": None, "projects": DEFAULT_PROJECTS, "core_order": None},
    "devops-en": {"language": "en", "path": ROOT / "html" / "cv-devops.pdf", "variant": "devops", "projects": ("p3", "p1", "p2"), "core_order": DEVOPS_CORE_ORDER},
    "devops-de": {"language": "de", "path": ROOT / "html" / "cv-devops-de.pdf", "variant": "devops", "projects": ("p3", "p1", "p2"), "core_order": DEVOPS_CORE_ORDER},
    "linux-admin-en": {"language": "en", "path": ROOT / "html" / "cv-linux-admin.pdf", "variant": "linux-admin", "projects": DEFAULT_PROJECTS, "core_order": LINUX_CORE_ORDER},
    "linux-admin-de": {"language": "de", "path": ROOT / "html" / "cv-linux-admin-de.pdf", "variant": "linux-admin", "projects": DEFAULT_PROJECTS, "core_order": LINUX_CORE_ORDER},
}
MANIFEST_PATH = ROOT / "content" / "pdf-provenance.json"
RENDERER_PATH = ROOT / "scripts" / "generate-pdfs.mjs"
PDF_TRANSLATION_KEYS = (
    "role",
    "pdf_profile_title", "pdf_profile_summary",
    "experience_title",
    "e1_dates", "e1_title", "e1_org", "e1_b1", "e1_b2",
    "e2_dates", "e2_title", "e2_org", "e2_b1",
    "e3_dates", "e3_title", "e3_org", "e3_b1",
    "e4_dates", "e4_title", "e4_org", "e4_b1",
    "pdf_projects_title",
    "p1_title", "pdf_p1_desc",
    "p2_title", "pdf_p2_desc",
    "p3_title", "pdf_p3_desc",
    "skills_title",
    "skills_core", "skills_core_items",
    "skills_working", "pdf_skills_working_items",
    "skills_learning", "skills_learning_items",
    "skills_foundations", "pdf_skills_foundations_items",
    "education_title",
    "ed1_dates", "ed1_title", "ed1_sub",
    "ed2_dates", "ed2_title", "ed2_sub",
    "ed3_dates", "ed3_title", "ed3_sub",
    "profile_languages_label",
    "profile_lang_latvian", "profile_lang_english", "profile_lang_german",
)
AVAILABILITY = {
    "en": "Available from January 2027",
    "de": "Verfügbar ab Januar 2027",
    "lv": "Pieejams no 2027. gada janvāra",
}
FORBIDDEN_TEXT = (
    "14-year logistics",
    "12+ Docker services",
    "100% uptime",
    "CI/CD-style",
    "Remote-friendly",
    "44319 Dortmund",
    "WhatsApp",
)


class PdfCheckError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PdfCheckError(f"invalid JSON: {path.relative_to(ROOT)}") from error


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as error:
        raise PdfCheckError(f"missing file: {path.relative_to(ROOT)}") from error


def pdf_projection(profile: dict[str, Any], translations: dict[str, dict[str, str]]) -> dict[str, Any]:
    try:
        projection = {
            "identity": {"name": profile["identity"]["name"], "career_goal": profile["identity"]["career_goal"]},
            "contact": {
                "email": profile["contact"]["email"],
                "phone": profile["contact"]["phone"],
                "github": profile["contact"]["github"],
                "website": profile["contact"]["website"],
            },
            "languages": profile["languages"],
            "translations": {
                language: {key: translations[language][key] for key in PDF_TRANSLATION_KEYS}
                for language in LANGUAGES
            },
            "renderer_sha256": sha256_file(RENDERER_PATH),
        }
    except KeyError as error:
        raise PdfCheckError(f"missing PDF-relevant canonical key: {error}") from error
    return projection


def expected_manifest(profile: dict[str, Any], translations: dict[str, dict[str, str]]) -> dict[str, Any]:
    projection = pdf_projection(profile, translations)
    return {
        "schema_version": 1,
        "pdf_source_sha256": sha256_bytes(canonical_json_bytes(projection)),
        "renderer_sha256": projection["renderer_sha256"],
        "pdfs": {
            case_id: {
                "path": str(case["path"].relative_to(ROOT)),
                "sha256": sha256_file(case["path"]),
            }
            for case_id, case in PDF_CASES.items()
        },
    }


def run_tool(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise PdfCheckError(f"tool failed: {' '.join(args)}: {detail.strip()}") from error
    return result.stdout


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def ordered_core_items(messages: dict[str, str], order: tuple[int, ...] | None) -> str:
    value = messages["skills_core_items"]
    if order is None:
        return value
    items = value.split(" · ")
    if len(items) != len(order) or set(order) != set(range(len(items))):
        raise PdfCheckError("invalid role-focused core skill ordering")
    return " · ".join(items[index] for index in order)


def role_for_case(language: str, variant: str | None, profile: dict[str, Any], messages: dict[str, str]) -> str:
    if variant is None:
        return messages["role"]
    if language == "en":
        match = re.match(r"^(.+?) or (.+?)(?:,|$)", profile["identity"]["career_goal"])
        if match is None:
            raise PdfCheckError("canonical career goal does not expose both role targets")
        return match.group(1) if variant == "devops" else match.group(2)
    if language == "de":
        roles = messages["role"].split(" / ")
        if len(roles) != 2:
            raise PdfCheckError("German canonical role does not expose both role targets")
        return roles[0] if variant == "devops" else roles[1]
    raise PdfCheckError(f"unsupported role-variant language: {language}")


def assert_in_order(text: str, values: list[str], language: str) -> None:
    searchable = normalize_text(text).casefold()
    position = -1
    for value in values:
        needle = normalize_text(value).casefold()
        next_position = searchable.find(needle, position + 1)
        if next_position < 0:
            raise PdfCheckError(f"{language} PDF missing ordered text: {value!r}")
        position = next_position


FORBIDDEN_LINK_PREFIXES = (
    "tel:",
    "sms:",
    "whatsapp:",
    "https://wa.me/",
    "https://api.whatsapp.com/",
)


def assert_pdf_link_targets(language: str, raw: str, expected_targets: tuple[str, ...]) -> None:
    if raw.count("/Subtype /Link") < len(expected_targets):
        raise PdfCheckError(f"{language} PDF is missing expected public contact links")
    for target in expected_targets:
        if f"/URI ({target})" not in raw:
            raise PdfCheckError(f"{language} PDF is missing canonical public link target: {target!r}")
    for prefix in FORBIDDEN_LINK_PREFIXES:
        if re.search(rf"/URI\s*\({re.escape(prefix)}", raw, flags=re.IGNORECASE):
            raise PdfCheckError(f"{language} PDF contains protected contact link target: {prefix!r}")


def inspect_pdf(case_id: str, case: dict[str, Any], profile: dict[str, Any], messages: dict[str, str]) -> None:
    language = case["language"]
    path = case["path"]
    role = role_for_case(language, case["variant"], profile, messages)
    core_items = ordered_core_items(messages, case["core_order"])
    if shutil.which("pdfinfo") is None or shutil.which("pdftotext") is None:
        raise PdfCheckError("pdfinfo and pdftotext are required; install poppler-utils")

    info = run_tool(["pdfinfo", str(path)])
    if not re.search(r"^Pages:\s+1\s*$", info, flags=re.MULTILINE):
        raise PdfCheckError(f"{language} PDF must contain exactly one page")
    if not re.search(r"^Tagged:\s+yes\s*$", info, flags=re.MULTILINE | re.IGNORECASE):
        raise PdfCheckError(f"{language} PDF must be tagged")

    raw = path.read_bytes().decode("latin1", errors="ignore")
    if "/StructTreeRoot" not in raw:
        raise PdfCheckError(f"{language} PDF is missing StructTreeRoot")
    if f"/Lang ({language})" not in raw:
        raise PdfCheckError(f"{language} PDF has incorrect document language")
    expected_link_targets = (
        f"mailto:{profile['contact']['email']['value']}",
        profile["contact"]["github"]["value"],
        profile["contact"]["website"]["value"],
    )
    assert_pdf_link_targets(language, raw, expected_link_targets)

    text = normalize_text(run_tool(["pdftotext", "-layout", str(path), "-"]))
    if not text:
        raise PdfCheckError(f"{language} PDF text extraction is empty")

    expected = [
        profile["identity"]["name"],
        role,
        AVAILABILITY[language],
        profile["contact"]["email"]["value"],
        "github.com/rozkalnsandris",
        "rozkalns.net",
        messages["pdf_profile_summary"],
        core_items,
        messages["pdf_skills_working_items"],
        messages["skills_learning_items"],
        messages["pdf_skills_foundations_items"],
        messages["p1_title"], messages["pdf_p1_desc"],
        messages["p3_title"], messages["pdf_p3_desc"],
        messages["p2_title"], messages["pdf_p2_desc"],
        messages["e1_title"], messages["e1_org"], messages["e1_dates"],
        messages["e2_title"], messages["e2_org"], messages["e2_dates"],
        messages["e3_title"], messages["e3_org"], messages["e3_dates"],
        messages["e4_title"], messages["e4_org"], messages["e4_dates"],
        messages["ed1_title"], messages["ed2_title"], messages["ed3_title"],
    ]
    for value in expected:
        if normalize_text(value) not in text:
            raise PdfCheckError(f"{language} PDF missing canonical text: {value!r}")

    assert_in_order(
        text,
        [
            messages["pdf_profile_title"],
            messages["skills_title"],
            messages["pdf_projects_title"],
            messages["experience_title"],
            messages["education_title"],
            messages["profile_languages_label"],
        ],
        language,
    )

    assert_in_order(
        text,
        [
            messages["pdf_projects_title"],
            *[messages[f"{prefix}_title"] for prefix in case["projects"]],
        ],
        language,
    )

    lowered = text.casefold()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden.casefold() in lowered:
            raise PdfCheckError(f"{language} PDF contains forbidden stale/private text: {forbidden!r}")


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write the reviewed PDF provenance manifest")
    args = parser.parse_args()
    try:
        profile = load_json(ROOT / "content" / "profile.json")
        translations = {
            language: load_json(ROOT / "content" / "translations" / f"{language}.json")
            for language in LANGUAGES
        }
        for case_id, case in PDF_CASES.items():
            language = case["language"]
            inspect_pdf(case_id, case, profile, translations[language])
        manifest = expected_manifest(profile, translations)
        if args.write:
            write_manifest(manifest)
        else:
            if load_json(MANIFEST_PATH) != manifest:
                raise PdfCheckError("PDF provenance manifest is stale; regenerate, inspect and accept the PDFs")
        print(f"PDF_SOURCE_SHA256={manifest['pdf_source_sha256']}")
        print("PDF_QUALITY=PASS")
    except PdfCheckError as error:
        print(f"PDF_QUALITY=FAIL ERROR={error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
