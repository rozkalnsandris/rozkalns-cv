#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "content" / "profile.json"
EVIDENCE_PATH = ROOT / "content" / "evidence.json"
MAX_VACANCY_CHARS = 262_144

CATEGORY_ORDER = ("evidenced", "working", "learning", "foundation", "not_in_canonical_profile")
GROUP_CATEGORY = {
    "core": "evidenced",
    "working": "working",
    "learning": "learning",
    "foundations": "foundation",
}

ALIASES: dict[str, tuple[str, ...]] = {
    "Linux administration": ("linux", "linux admin", "linux system administration", "linux systems administration"),
    "Docker Compose": ("docker compose", "docker-compose", "compose"),
    "SSL/TLS": ("ssl", "tls", "ssl/tls", "https certificates"),
    "REST APIs": ("rest api", "rest apis", "restful api", "restful apis"),
    "Home Assistant": ("home assistant", "homeassistant"),
    "ESP32/IoT": ("esp32", "iot", "esp32/iot"),
    "AWS Cloud": ("aws", "aws cloud", "amazon web services"),
    "SSH/FTP": ("ssh", "ftp", "ssh/ftp"),
    "PHP/IPB forums": ("php", "ipb", "ipb forums", "php/ipb forums"),
    "HTML/CSS": ("html", "css", "html/css"),
}

GAP_TERMS: dict[str, tuple[str, ...]] = {
    "Argo CD": ("argo cd", "argocd"),
    "Azure": ("azure", "microsoft azure"),
    "CI/CD": ("ci/cd", "ci cd"),
    "Google Cloud": ("google cloud", "gcp"),
    "Helm": ("helm",),
    "Jenkins": ("jenkins",),
    "Kafka": ("kafka",),
    "Kubernetes": ("kubernetes", "k8s"),
    "MySQL": ("mysql",),
    "OpenShift": ("openshift",),
    "PostgreSQL": ("postgresql", "postgres"),
    "Pulumi": ("pulumi",),
    "Redis": ("redis",),
    "RHEL": ("rhel", "red hat enterprise linux"),
    "Vault": ("hashicorp vault", "vault"),
}


class CanonicalDataError(RuntimeError):
    pass


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", " ", value.casefold()).strip()


def _contains_phrase(normalized_text: str, phrase: str) -> bool:
    normalized_phrase = _normalize(phrase)
    if not normalized_phrase:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(normalized_phrase).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def _load_canonical_data() -> tuple[dict[str, object], dict[str, object]]:
    try:
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CanonicalDataError("canonical profile/evidence unavailable or invalid") from exc
    return profile, evidence


def _proof_items(skill: str, registry: dict[str, object]) -> list[dict[str, str]]:
    mappings = registry.get("skill_evidence", {})
    evidence = registry.get("evidence", {})
    if not isinstance(mappings, dict) or not isinstance(evidence, dict):
        raise CanonicalDataError("canonical evidence registry shape is invalid")
    ids = mappings.get(skill, [])
    if not isinstance(ids, list):
        raise CanonicalDataError("canonical evidence mapping shape is invalid")
    proof: list[dict[str, str]] = []
    for evidence_id in ids:
        item = evidence.get(evidence_id)
        if not isinstance(evidence_id, str) or not isinstance(item, dict) or not isinstance(item.get("url"), str):
            raise CanonicalDataError("canonical evidence reference is invalid")
        proof.append({"id": evidence_id, "url": item["url"]})
    return proof


def analyze_vacancy(text: str, profile: dict[str, object], registry: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    normalized_text = _normalize(text)
    skills = profile.get("skills")
    if not isinstance(skills, dict):
        raise CanonicalDataError("canonical skill taxonomy is invalid")

    categories: dict[str, list[dict[str, object]]] = {category: [] for category in CATEGORY_ORDER}
    matched_aliases: set[str] = set()

    for group in ("core", "working", "learning", "foundations"):
        group_skills = skills.get(group)
        if not isinstance(group_skills, list):
            raise CanonicalDataError("canonical skill group is invalid")
        for skill in group_skills:
            if not isinstance(skill, str):
                raise CanonicalDataError("canonical skill is invalid")
            aliases = (skill, *ALIASES.get(skill, ()))
            if skill == "Docker":
                matching_aliases = [
                    "Docker"
                    for _ in [0]
                    if re.search(r"(?<![a-z0-9])docker(?!\s+compose)(?![a-z0-9])", normalized_text)
                ]
            else:
                matching_aliases = [alias for alias in aliases if _contains_phrase(normalized_text, alias)]
            if not matching_aliases:
                continue
            matched_aliases.update(_normalize(alias) for alias in matching_aliases)
            proof = _proof_items(skill, registry)
            category = GROUP_CATEGORY[group]
            if category == "evidenced" and not proof:
                raise CanonicalDataError(f"core skill lacks canonical public evidence: {skill}")
            if category in {"learning", "foundation"}:
                proof = []
            categories[category].append(
                {
                    "requirement": skill,
                    "canonical_skill": skill,
                    "profile_group": group,
                    "evidence": proof,
                }
            )

    for requirement, aliases in GAP_TERMS.items():
        matching_aliases = [alias for alias in aliases if _contains_phrase(normalized_text, alias)]
        if not matching_aliases:
            continue
        if any(_normalize(alias) in matched_aliases for alias in matching_aliases):
            continue
        categories["not_in_canonical_profile"].append(
            {
                "requirement": requirement,
                "canonical_skill": None,
                "profile_group": None,
                "evidence": [],
            }
        )

    for entries in categories.values():
        entries.sort(key=lambda item: str(item["requirement"]).casefold())
    return categories


def _read_limited(stream: object) -> str:
    text = stream.read(MAX_VACANCY_CHARS + 1)
    if len(text) > MAX_VACANCY_CHARS:
        raise ValueError("vacancy input exceeds local safety limit")
    return text


def _read_input(local_file: str | None) -> tuple[str, str]:
    if local_file is None:
        return _read_limited(sys.stdin), "stdin"
    try:
        with Path(local_file).expanduser().open("r", encoding="utf-8") as handle:
            return _read_limited(handle), "local-file"
    except (OSError, UnicodeError) as exc:
        raise ValueError("unable to read local vacancy file") from exc


def _human_report(categories: dict[str, list[dict[str, object]]]) -> str:
    labels = {
        "evidenced": "EVIDENCED",
        "working": "WORKING KNOWLEDGE",
        "learning": "LEARNING — NOT PROVEN",
        "foundation": "CANONICAL FOUNDATION — NOT PROMOTED",
        "not_in_canonical_profile": "NOT IN CANONICAL PROFILE",
    }
    lines = ["Vacancy evidence-gap report (advisory; no score or hiring prediction)"]
    for category in CATEGORY_ORDER:
        lines.extend(("", labels[category]))
        entries = categories[category]
        if not entries:
            lines.append("- none")
            continue
        for item in entries:
            proof = item["evidence"]
            suffix = ""
            if proof:
                suffix = " — proof: " + ", ".join(str(entry["url"]) for entry in proof)
            lines.append(f"- {item['requirement']}{suffix}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare local vacancy text with canonical CV skills and public evidence without modifying the CV."
    )
    parser.add_argument("--file", metavar="PATH", help="read vacancy text from an explicit local file instead of stdin")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit deterministic JSON to stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        text, source = _read_input(args.file)
        if not text.strip():
            raise ValueError("vacancy input is empty")
        profile, registry = _load_canonical_data()
        categories = analyze_vacancy(text, profile, registry)
    except (ValueError, CanonicalDataError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        payload = {"schema_version": 1, "source": source, "categories": categories}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(_human_report(categories))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
