from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


DEFAULT_EVIDENCE_PATH = Path(__file__).with_name("evidence_registry.json")
URL_POLICY_BLOCK_REPLY = (
    "I can only share approved public CV links. "
    "Please ask for evidence from the public CV."
)
_URL_START_RE = re.compile(r"(?i)https?://")
_URL_BOUNDARY_CHARS = frozenset(" \t\r\n<>\"'()[]{}.,;!?")


class EvidenceRegistryError(RuntimeError):
    """Raised when the generated runtime evidence registry is invalid."""


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    url: str


class EvidenceRegistry:
    """Strict, generated allowlist for recruiter-facing public proof links."""

    def __init__(self, payload: dict[str, Any]) -> None:
        expected = {
            "schema_version",
            "evidence",
            "skill_evidence",
            "project_evidence",
            "project_titles",
            "allowed_output_urls",
        }
        if set(payload) != expected or payload.get("schema_version") != 1:
            raise EvidenceRegistryError("runtime evidence schema is invalid")

        evidence = payload.get("evidence")
        if not isinstance(evidence, dict) or not evidence:
            raise EvidenceRegistryError("runtime evidence must be a non-empty object")
        self._evidence: dict[str, EvidenceRecord] = {}
        for evidence_id, row in evidence.items():
            if (
                not isinstance(evidence_id, str)
                or not evidence_id
                or not isinstance(row, dict)
                or set(row) != {"url"}
                or not isinstance(row.get("url"), str)
                or not row["url"].startswith("https://")
            ):
                raise EvidenceRegistryError("runtime evidence entry is invalid")
            self._evidence[evidence_id] = EvidenceRecord(evidence_id, row["url"])

        self._skill_evidence = self._validate_mapping(
            payload.get("skill_evidence"), "skill_evidence"
        )
        self._project_evidence = self._validate_mapping(
            payload.get("project_evidence"), "project_evidence"
        )
        titles = payload.get("project_titles")
        if not isinstance(titles, dict) or set(titles) != set(self._project_evidence):
            raise EvidenceRegistryError("project_titles do not match project evidence")
        if any(not isinstance(value, str) or not value.strip() for value in titles.values()):
            raise EvidenceRegistryError("project title is invalid")
        self._project_titles = {key: value.strip() for key, value in titles.items()}

        allowed = payload.get("allowed_output_urls")
        if not isinstance(allowed, list) or not allowed or len(set(allowed)) != len(allowed):
            raise EvidenceRegistryError("allowed_output_urls are invalid")
        if any(not isinstance(url, str) or not url.startswith("https://") for url in allowed):
            raise EvidenceRegistryError("allowed output URL is invalid")
        evidence_urls = {record.url for record in self._evidence.values()}
        if not evidence_urls.issubset(set(allowed)):
            raise EvidenceRegistryError("evidence URLs are missing from output allowlist")
        self.allowed_output_urls = tuple(allowed)

    def _validate_mapping(self, value: Any, label: str) -> dict[str, tuple[str, ...]]:
        if not isinstance(value, dict):
            raise EvidenceRegistryError(f"{label} must be an object")
        result: dict[str, tuple[str, ...]] = {}
        for key, ids in value.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(ids, list):
                raise EvidenceRegistryError(f"{label} entry is invalid")
            if not ids or len(set(ids)) != len(ids):
                raise EvidenceRegistryError(f"{label} ids are invalid")
            if any(not isinstance(item, str) or item not in self._evidence for item in ids):
                raise EvidenceRegistryError(f"{label} references unknown evidence")
            result[key.strip()] = tuple(ids)
        return result

    @classmethod
    def load(cls, path: Path | None = None) -> "EvidenceRegistry":
        source = DEFAULT_EVIDENCE_PATH if path is None else path
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise EvidenceRegistryError("generated runtime evidence is unreadable") from error
        if not isinstance(payload, dict):
            raise EvidenceRegistryError("generated runtime evidence must be an object")
        return cls(payload)

    def select(self, question: str, *, limit: int = 3) -> tuple[EvidenceRecord, ...]:
        if limit < 1:
            return ()
        normalized = " ".join(str(question).casefold().split())
        selected: list[str] = []

        for skill in sorted(self._skill_evidence, key=len, reverse=True):
            if skill.casefold() in normalized:
                selected.extend(self._skill_evidence[skill])

        for project_id, evidence_ids in self._project_evidence.items():
            aliases = {
                project_id.casefold().replace("-", " "),
                self._project_titles[project_id].casefold(),
            }
            if any(alias and alias in normalized for alias in aliases):
                selected.extend(evidence_ids)

        unique: list[EvidenceRecord] = []
        seen: set[str] = set()
        for evidence_id in selected:
            if evidence_id in seen:
                continue
            seen.add(evidence_id)
            unique.append(self._evidence[evidence_id])
            if len(unique) == limit:
                break
        return tuple(unique)

    @staticmethod
    def _label(question: str) -> str:
        text = str(question).casefold()
        if re.search(r"[āčēģīķļņšūž]", text) or any(
            token in text for token in ("pierād", "prasme", "projekts", "kā ")
        ):
            return "Publiskie pierādījumi:"
        if re.search(r"[äöüß]", text) or any(
            token in text for token in ("nachweis", "beleg", "welche", "projekt", "erfahrung")
        ):
            return "Öffentliche Nachweise:"
        return "Public evidence:"

    def render_appendix(self, question: str, *, limit: int = 3) -> str:
        records = self.select(question, limit=limit)
        if not records:
            return ""
        lines = ["", "", self._label(question)]
        lines.extend(f"- {record.evidence_id}: {record.url}" for record in records)
        return "\n".join(lines)


class ApprovedUrlStreamGuard:
    """Reject provider-generated URLs unless they exactly match the allowlist."""

    def __init__(self, allowed_urls: tuple[str, ...] | list[str]) -> None:
        self.allowed_urls = tuple(allowed_urls)
        if not self.allowed_urls:
            raise ValueError("approved URL allowlist must not be empty")
        self.pending = ""
        self.blocked = False

    def _block(self) -> list[str]:
        self.pending = ""
        self.blocked = True
        return [URL_POLICY_BLOCK_REPLY]

    @staticmethod
    def _is_boundary(character: str) -> bool:
        return character in _URL_BOUNDARY_CHARS

    def _drain(self, *, final: bool) -> list[str]:
        emitted: list[str] = []
        while self.pending and not self.blocked:
            match = _URL_START_RE.search(self.pending)
            if match is None:
                if final:
                    emitted.append(self.pending)
                    self.pending = ""
                else:
                    keep = min(8, len(self.pending))
                    emit_length = len(self.pending) - keep
                    if emit_length <= 0:
                        break
                    emitted.append(self.pending[:emit_length])
                    self.pending = self.pending[emit_length:]
                continue

            if match.start() > 0:
                emitted.append(self.pending[: match.start()])
                self.pending = self.pending[match.start() :]
                continue

            prefix_matches = [url for url in self.allowed_urls if url.startswith(self.pending)]
            if prefix_matches:
                if final:
                    return emitted + self._block()
                break

            exact_prefixes = [url for url in self.allowed_urls if self.pending.startswith(url)]
            if not exact_prefixes:
                return emitted + self._block()
            approved = max(exact_prefixes, key=len)
            if len(self.pending) == len(approved):
                if final:
                    emitted.append(approved)
                    self.pending = ""
                break

            next_character = self.pending[len(approved)]
            if not self._is_boundary(next_character):
                longer = [url for url in self.allowed_urls if url.startswith(self.pending)]
                if longer and not final:
                    break
                return emitted + self._block()
            emitted.append(approved)
            self.pending = self.pending[len(approved) :]
        return emitted

    def feed(self, chunk: str) -> list[str]:
        if self.blocked or not chunk:
            return []
        self.pending += chunk
        return self._drain(final=False)

    def finish(self) -> list[str]:
        if self.blocked:
            return []
        return self._drain(final=True)
