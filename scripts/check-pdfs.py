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
PROJECTS = ("p8", "p1", "p3")
GROUP_ORDERS = {
    "master": ("linux_operations", "networking_web", "containers_monitoring", "application_support", "automation_git"),
    "technical-support": ("linux_operations", "networking_web", "application_support", "containers_monitoring", "automation_git"),
    "linux-operations": ("linux_operations", "containers_monitoring", "networking_web", "automation_git", "application_support"),
    "application-support": ("application_support", "networking_web", "linux_operations", "containers_monitoring", "automation_git"),
}
PDF_CASES = {
    "en": {"language":"en","path":ROOT/"html/cv.pdf","variant":None,"group_order":GROUP_ORDERS["master"]},
    "de": {"language":"de","path":ROOT/"html/cv-de.pdf","variant":None,"group_order":GROUP_ORDERS["master"]},
    "lv": {"language":"lv","path":ROOT/"html/cv-lv.pdf","variant":None,"group_order":GROUP_ORDERS["master"]},
    "technical-support-en": {"language":"en","path":ROOT/"html/cv-technical-support.pdf","variant":"technical-support","group_order":GROUP_ORDERS["technical-support"]},
    "technical-support-de": {"language":"de","path":ROOT/"html/cv-technical-support-de.pdf","variant":"technical-support","group_order":GROUP_ORDERS["technical-support"]},
    "linux-operations-en": {"language":"en","path":ROOT/"html/cv-linux-operations.pdf","variant":"linux-operations","group_order":GROUP_ORDERS["linux-operations"]},
    "linux-operations-de": {"language":"de","path":ROOT/"html/cv-linux-operations-de.pdf","variant":"linux-operations","group_order":GROUP_ORDERS["linux-operations"]},
    "application-support-en": {"language":"en","path":ROOT/"html/cv-application-support.pdf","variant":"application-support","group_order":GROUP_ORDERS["application-support"]},
    "application-support-de": {"language":"de","path":ROOT/"html/cv-application-support-de.pdf","variant":"application-support","group_order":GROUP_ORDERS["application-support"]},
}
VARIANT_ROLES = {
    "en": {"technical-support":"Junior Technical Support Engineer","linux-operations":"Junior Linux Operations","application-support":"Application Support Engineer"},
    "de": {"technical-support":"Junior Technical Support","linux-operations":"Junior Linux Operations","application-support":"Application Support Engineer"},
}
MANIFEST_PATH = ROOT / "content/pdf-provenance.json"
RENDERER_PATH = ROOT / "scripts/generate-pdfs.mjs"
GROUP_KEYS = {g:(f"skill_group_{g}", f"skill_group_{g}_items") for g in GROUP_ORDERS["master"]}
PDF_TRANSLATION_KEYS = (
    "role", "pdf_profile_title", "pdf_profile_summary", "experience_title",
    "e1_dates","e1_title","e1_org","e1_b1", "e2_dates","e2_title","e2_org","e2_b1",
    "e3_dates","e3_title","e3_org","e3_b1", "e4_dates","e4_title","e4_org","e4_b1",
    "e5_dates","e5_title","e5_org","e5_b1", "pdf_projects_title",
    "p8_title","pdf_p8_desc","p1_title","pdf_p1_desc","p3_title","pdf_p3_desc",
    "skills_title", "education_title", "ed1_dates","ed1_title","ed1_sub", "ed2_dates","ed2_title","ed2_sub", "ed3_dates","ed3_title","ed3_sub",
    "profile_languages_label","profile_lang_latvian","profile_lang_english","profile_lang_german",
    *tuple(key for group in GROUP_ORDERS["master"] for key in GROUP_KEYS[group]),
)
AVAILABILITY = {"en":"Available from January 2027","de":"Verfügbar ab Januar 2027","lv":"Pieejams no 2027. gada janvāra"}
FORBIDDEN_TEXT = ("Junior DevOps & Linux Engineer", "Junior DevOps Engineer", "MLOps", "14-year logistics", "12+ Docker services", "100% uptime", "44319 Dortmund", "WhatsApp")
FORBIDDEN_LINK_PREFIXES = ("tel:", "sms:", "whatsapp:", "https://wa.me/", "https://api.whatsapp.com/")

class PdfCheckError(RuntimeError): pass

def load_json(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise PdfCheckError(f"invalid JSON: {path.relative_to(ROOT)}") from error

def canonical_json_bytes(value: Any) -> bytes: return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
def sha256_bytes(content: bytes) -> str: return hashlib.sha256(content).hexdigest()
def sha256_file(path: Path) -> str:
    try: return sha256_bytes(path.read_bytes())
    except OSError as error: raise PdfCheckError(f"missing file: {path.relative_to(ROOT)}") from error

def pdf_projection(profile: dict[str, Any], translations: dict[str, dict[str, str]]) -> dict[str, Any]:
    try:
        return {
            "profile": profile,
            "translations": {language:{key:translations[language][key] for key in PDF_TRANSLATION_KEYS} for language in LANGUAGES},
            "renderer_sha256": sha256_file(RENDERER_PATH),
        }
    except KeyError as error: raise PdfCheckError(f"missing PDF-relevant canonical key: {error}") from error

def expected_manifest(profile: dict[str, Any], translations: dict[str, dict[str, str]]) -> dict[str, Any]:
    projection = pdf_projection(profile, translations)
    return {"schema_version":1,"pdf_source_sha256":sha256_bytes(canonical_json_bytes(projection)),"renderer_sha256":projection["renderer_sha256"],"pdfs":{case_id:{"path":str(case["path"].relative_to(ROOT)),"sha256":sha256_file(case["path"])} for case_id,case in PDF_CASES.items()}}

def run_tool(args: list[str]) -> str:
    try:
        result = subprocess.run(args, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise PdfCheckError(f"tool failed: {' '.join(args)}: {detail.strip()}") from error
    return result.stdout

def normalize_text(text: str) -> str: return re.sub(r"\s+", " ", text).strip()
def role_for_case(language: str, variant: str | None, messages: dict[str,str]) -> str:
    if variant is None: return messages["role"]
    try: return VARIANT_ROLES[language][variant]
    except KeyError as error: raise PdfCheckError(f"unsupported role variant: {language}:{variant}") from error

def expected_title(profile: dict[str,Any], language: str, role: str) -> str:
    return f"{profile['identity']['name']} - {role} - {'Lebenslauf' if language == 'de' else 'CV'}"

def assert_in_order(text: str, values: list[str], case_id: str) -> None:
    searchable = normalize_text(text).casefold(); position = -1
    for value in values:
        needle = normalize_text(value).casefold(); next_position = searchable.find(needle, position + 1)
        if next_position < 0: raise PdfCheckError(f"{case_id} PDF missing ordered text: {value!r}")
        position = next_position

def assert_pdf_link_targets(case_id: str, raw: str, expected_targets: tuple[str,...]) -> None:
    if raw.count("/Subtype /Link") < len(expected_targets): raise PdfCheckError(f"{case_id} PDF is missing expected public contact links")
    for target in expected_targets:
        if f"/URI ({target})" not in raw: raise PdfCheckError(f"{case_id} PDF is missing canonical public link target: {target!r}")
    for prefix in FORBIDDEN_LINK_PREFIXES:
        if re.search(rf"/URI\s*\({re.escape(prefix)}", raw, flags=re.I): raise PdfCheckError(f"{case_id} PDF contains protected contact link target: {prefix!r}")

def inspect_pdf(case_id: str, case: dict[str,Any], profile: dict[str,Any], messages: dict[str,str]) -> None:
    language = case["language"]; path = case["path"]; role = role_for_case(language, case["variant"], messages)
    if shutil.which("pdfinfo") is None or shutil.which("pdftotext") is None: raise PdfCheckError("pdfinfo and pdftotext are required; install poppler-utils")
    info = run_tool(["pdfinfo", str(path)])
    match = re.search(r"^Pages:\s+(\d+)\s*$", info, flags=re.M)
    if match is None or int(match.group(1)) not in (1,2): raise PdfCheckError(f"{case_id} PDF must contain one or two pages")
    if not re.search(r"^Tagged:\s+yes\s*$", info, flags=re.M|re.I): raise PdfCheckError(f"{case_id} PDF must be tagged")
    title_match = re.search(r"^Title:\s*(.+?)\s*$", info, flags=re.M)
    if title_match is None or title_match.group(1).strip() != expected_title(profile, language, role): raise PdfCheckError(f"{case_id} PDF title metadata is incorrect")
    raw = path.read_bytes().decode("latin1", errors="ignore")
    if "/StructTreeRoot" not in raw: raise PdfCheckError(f"{case_id} PDF is missing StructTreeRoot")
    if f"/Lang ({language})" not in raw: raise PdfCheckError(f"{case_id} PDF has incorrect document language")
    assert_pdf_link_targets(case_id, raw, (f"mailto:{profile['contact']['email']['value']}", profile['contact']['github']['value'], profile['contact']['website']['value']))
    text = normalize_text(run_tool(["pdftotext", "-layout", str(path), "-"]))
    if not text: raise PdfCheckError(f"{case_id} PDF text extraction is empty")
    expected = [profile["identity"]["name"], role, AVAILABILITY[language], profile["contact"]["email"]["value"], "github.com/rozkalnsandris", "rozkalns.net", messages["pdf_profile_summary"]]
    for group in case["group_order"]:
        label_key, items_key = GROUP_KEYS[group]; expected.extend([messages[label_key], messages[items_key]])
    for prefix in PROJECTS: expected.extend([messages[f"{prefix}_title"], messages[f"pdf_{prefix}_desc"]])
    for i in range(1,6): expected.extend([messages[f"e{i}_title"], messages[f"e{i}_org"], messages[f"e{i}_dates"]])
    expected.extend([messages["ed1_title"], messages["ed2_title"], messages["ed3_title"]])
    for value in expected:
        if normalize_text(value) not in text: raise PdfCheckError(f"{case_id} PDF missing canonical text: {value!r}")
    assert_in_order(text, [messages["pdf_profile_title"], messages["skills_title"], messages["pdf_projects_title"], messages["experience_title"], messages["education_title"], messages["profile_languages_label"]], case_id)
    for forbidden in FORBIDDEN_TEXT:
        if forbidden.casefold() in text.casefold(): raise PdfCheckError(f"{case_id} PDF contains forbidden stale/private text: {forbidden!r}")

def write_manifest(manifest: dict[str,Any]) -> None: MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--write", action="store_true"); args = parser.parse_args()
    try:
        profile = load_json(ROOT/"content/profile.json"); translations = {language:load_json(ROOT/f"content/translations/{language}.json") for language in LANGUAGES}
        for case_id, case in PDF_CASES.items(): inspect_pdf(case_id, case, profile, translations[case["language"]])
        manifest = expected_manifest(profile, translations)
        if args.write: write_manifest(manifest)
        elif load_json(MANIFEST_PATH) != manifest: raise PdfCheckError("PDF provenance manifest is stale; regenerate, inspect and accept the PDFs")
        print(f"PDF_SOURCE_SHA256={manifest['pdf_source_sha256']}"); print("PDF_QUALITY=PASS")
    except PdfCheckError as error:
        print(f"PDF_QUALITY=FAIL ERROR={error}", file=sys.stderr); return 1
    return 0
if __name__ == "__main__": raise SystemExit(main())
