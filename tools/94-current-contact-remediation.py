#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import fitz

ROOT = Path(__file__).resolve().parents[1]
TODAY = "2026-08-08"
VERSION_RE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})\.([1-9][0-9]*)$")
EMAIL_RE = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def render_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def next_content_version(current: str) -> str:
    match = VERSION_RE.fullmatch(current)
    if not match:
        raise SystemExit("profile.content_version is not in the expected format")
    day, serial_text = match.groups()
    serial = int(serial_text)
    return f"{TODAY}.{serial + 1}" if day == TODAY else f"{TODAY}.1"


def privacy_clean_pdfs(protected: dict[str, str]) -> None:
    for name in ("cv.pdf", "cv-de.pdf", "cv-lv.pdf"):
        path = ROOT / "html" / name
        document = fitz.open(path)
        original_pages = len(document)
        hits = {"email": 0, "phone": 0, "phone_uri": 0}
        removed_links = 0
        for page in document:
            for key, value in protected.items():
                for rect in page.search_for(value):
                    hits[key] += 1
                    expanded = fitz.Rect(
                        max(page.rect.x0, rect.x0 - 7),
                        max(page.rect.y0, rect.y0 - 1),
                        min(page.rect.x1, rect.x1 + 7),
                        min(page.rect.y1, rect.y1 + 1),
                    )
                    page.add_redact_annot(expanded, fill=(1, 1, 1))
            for link in list(page.get_links()):
                uri = str(link.get("uri") or "")
                if uri.startswith("mailto:") or uri.startswith("tel:"):
                    page.delete_link(link)
                    removed_links += 1
            page.apply_redactions()
        if hits["email"] < 1 or hits["phone"] < 1:
            raise SystemExit(f"{name}: expected protected contact text was not found")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{name}.", suffix=".pdf", dir=path.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            document.save(temporary, garbage=4, deflate=True, clean=True)
            document.close()
            clean = fitz.open(temporary)
            if len(clean) != original_pages:
                raise SystemExit(f"{name}: page count changed during privacy redaction")
            text = "".join(page.get_text() for page in clean)
            if any(value in text for value in protected.values()):
                raise SystemExit(f"{name}: protected text remains after privacy redaction")
            for page in clean:
                for link in page.get_links():
                    uri = str(link.get("uri") or "")
                    if uri.startswith("mailto:") or uri.startswith("tel:"):
                        raise SystemExit(f"{name}: protected contact link remains")
            clean.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        print(
            f"PDF_PRIVACY_REDACTED={name};pages:{original_pages};"
            f"email_hits:{hits['email']};phone_hits:{hits['phone']};links_removed:{removed_links}"
        )


def migrate_profile() -> dict[str, str]:
    path = ROOT / "content/profile.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("schema_version") != 1:
        raise SystemExit("profile schema is not the expected v1 input")
    contact = profile.get("contact")
    if not isinstance(contact, dict):
        raise SystemExit("profile contact object is missing")
    email = contact.get("email")
    phone = contact.get("phone")
    if not isinstance(email, dict) or set(email) != {"value", "visibility"}:
        raise SystemExit("email contact input shape drifted")
    if not isinstance(phone, dict) or set(phone) != {"value", "uri", "visibility"}:
        raise SystemExit("phone contact input shape drifted")
    if email.get("visibility") != "public" or phone.get("visibility") != "public":
        raise SystemExit("protected contacts are not in the expected legacy public state")
    protected = {
        "email": str(email["value"]),
        "phone": str(phone["value"]),
        "phone_uri": str(phone["uri"]),
    }
    if not EMAIL_RE.fullmatch(protected["email"]):
        raise SystemExit("legacy email shape is invalid")
    if not re.fullmatch(r"\+[0-9]{8,15}", protected["phone_uri"]):
        raise SystemExit("legacy phone URI shape is invalid")

    privacy_clean_pdfs(protected)

    profile["schema_version"] = 2
    profile["content_version"] = next_content_version(str(profile["content_version"]))
    profile["contact"]["email"] = {"visibility": "runtime-protected"}
    profile["contact"]["phone"] = {"visibility": "runtime-protected"}
    path.write_text(render_json(profile), encoding="utf-8")
    print("PROFILE_CONTACT_MODEL=runtime-protected")
    return protected


def migrate_schema() -> None:
    path = ROOT / "content/profile.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    if schema["properties"]["schema_version"].get("const") != 1:
        raise SystemExit("profile schema contract drifted")
    schema["title"] = "Canonical CV profile"
    schema["properties"]["schema_version"] = {"const": 2}
    contact = schema["properties"]["contact"]["properties"]
    contact["email"] = {"$ref": "#/$defs/protectedValue"}
    contact["phone"] = {"$ref": "#/$defs/protectedValue"}
    schema["$defs"]["protectedValue"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["visibility"],
        "properties": {"visibility": {"const": "runtime-protected"}},
    }
    path.write_text(render_json(schema), encoding="utf-8")


def migrate_builder() -> None:
    path = "scripts/build-content.py"
    text = read(path)
    text = replace_once(
        text,
        'PHONE_RE = re.compile(r"^\\+[0-9]{8,15}$")\n',
        "",
        "remove obsolete phone regex",
    )
    text = replace_once(
        text,
        '    if profile["schema_version"] != 1:\n        raise ContentError("profile.schema_version must be 1")',
        '    if profile["schema_version"] != 2:\n        raise ContentError("profile.schema_version must be 2")',
        "profile schema version",
    )
    old_contact = '''    for key in ("email", "github", "website"):\n        entry = require_object(\n            contact[key], f"profile.contact.{key}", {"value", "visibility"}\n        )\n        require_text(entry["value"], f"profile.contact.{key}.value", 2)\n        if entry["visibility"] != "public":\n            raise ContentError(f"profile.contact.{key} must be public")\n    phone = require_object(\n        contact["phone"],\n        "profile.contact.phone",\n        {"value", "uri", "visibility"},\n    )\n    require_text(phone["value"], "profile.contact.phone.value", 2)\n    if phone["visibility"] != "public" or not PHONE_RE.fullmatch(\n        require_text(phone["uri"], "profile.contact.phone.uri")\n    ):\n        raise ContentError("profile.contact.phone is invalid")\n'''
    new_contact = '''    for key in ("email", "phone"):\n        entry = require_object(\n            contact[key], f"profile.contact.{key}", {"visibility"}\n        )\n        if entry["visibility"] != "runtime-protected":\n            raise ContentError(f"profile.contact.{key} must be runtime-protected")\n    for key in ("github", "website"):\n        entry = require_object(\n            contact[key], f"profile.contact.{key}", {"value", "visibility"}\n        )\n        require_text(entry["value"], f"profile.contact.{key}.value", 2)\n        if entry["visibility"] != "public":\n            raise ContentError(f"profile.contact.{key} must be public")\n'''
    text = replace_once(text, old_contact, new_contact, "contact validation")
    old_prompt = '''        "PUBLIC CONTACT",\n        f"Email: {contact['email']['value']}",\n        f"Phone: {contact['phone']['value']}",\n        f"GitHub: {contact['github']['value']}",\n        f"Website: {contact['website']['value']}",\n'''
    new_prompt = '''        "PUBLIC CONTACT",\n        "Email and phone: available only through the verified contact section on the public CV.",\n        f"GitHub: {contact['github']['value']}",\n        f"Website: {contact['website']['value']}",\n'''
    text = replace_once(text, old_prompt, new_prompt, "assistant public contact block")
    text = replace_once(
        text,
        '            "- Do not reveal personal data beyond the public contact and facts listed above.",',
        '            "- Do not reveal, infer, or guess protected email or phone details; direct contact requests to the verified contact section on the public CV.",',
        "assistant privacy rule",
    )
    write(path, text)


def migrate_bootstrap(protected_email: str) -> None:
    path = "scripts/bootstrap-github.sh"
    text = read(path)
    pattern = re.compile(
        r"git config user\.email >/dev/null 2>&1 \|\| git config user\.email (?P<quote>['\"])(?P<value>[^'\"]+)(?P=quote)"
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"bootstrap email fallback count drifted: {len(matches)}")
    if matches[0].group("value") != protected_email:
        raise SystemExit("bootstrap email fallback does not match canonical protected email")
    replacement = (
        'git config user.email >/dev/null 2>&1 || '
        'git config user.email "${GIT_AUTHOR_EMAIL:?Set GIT_AUTHOR_EMAIL before running bootstrap-github.sh}"'
    )
    write(path, pattern.sub(replacement, text, count=1))


def migrate_docs() -> None:
    path = "docs/CONTENT_AUTHORING.md"
    text = read(path)
    text = replace_once(
        text,
        "- `content/profile.json` — public professional facts and structured records;",
        "- `content/profile.json` — public professional facts, structured records, and runtime-protected contact-channel metadata;",
        "authoring source description",
    )
    text = replace_once(
        text,
        "- `bot/system_prompt.txt` from public canonical profile facts;",
        "- `bot/system_prompt.txt` from public canonical profile facts, excluding runtime-protected email and phone values;",
        "assistant generated output description",
    )
    text = replace_once(
        text,
        "3. confirm the public phone, email, GitHub, website, role, availability, work\n   history, projects, skills, and education match `content/profile.json` and the\n   corresponding translation;",
        "3. confirm runtime-protected email/phone values and contact links are absent from\n   every PDF, while public GitHub, website, role, availability, work history,\n   projects, skills, and education remain correct;",
        "PDF privacy checklist",
    )
    text = replace_once(
        text,
        "- the assistant prompt contains only public canonical facts;",
        "- the assistant prompt contains only public canonical facts and directs email/phone requests to the verified contact section;",
        "review privacy checklist",
    )
    write(path, text)


def run(*command: str) -> None:
    completed = subprocess.run(command, cwd=ROOT, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(command)}")


def assert_old_values_absent(protected: dict[str, str]) -> None:
    tracked = [
        raw.decode("utf-8")
        for raw in subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
        if raw
    ]
    hits: list[str] = []
    candidates = [value.encode("utf-8") for value in protected.values()]
    for relative in tracked:
        path = ROOT / relative
        if not path.is_file():
            continue
        data = path.read_bytes()
        if any(candidate in data for candidate in candidates):
            hits.append(relative)
    if hits:
        print("CURRENT_TREE_PRIVACY_SCAN=FAIL")
        for relative in hits:
            print(f"CURRENT_TREE_PRIVACY_HIT_FILE={relative}")
        raise SystemExit("protected legacy contact values remain in tracked current tree")
    print("CURRENT_TREE_PRIVACY_SCAN=PASS")


def main() -> int:
    protected = migrate_profile()
    migrate_schema()
    migrate_builder()
    migrate_bootstrap(protected["email"])
    migrate_docs()

    run(sys.executable, "scripts/build-content.py", "--write", "--accept-pdfs")
    run(sys.executable, "scripts/sync-system-prompt.py", "--write")
    run(sys.executable, "scripts/build-content.py", "--check")
    run(sys.executable, "scripts/sync-system-prompt.py", "--check")
    assert_old_values_absent(protected)
    print("CURRENT_CONTACT_REMEDIATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
