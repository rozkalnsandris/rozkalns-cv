from __future__ import annotations

import re
from collections.abc import Iterable


BLOCKED_CONTACT_REPLY = (
    "I can’t provide phone or direct WhatsApp details in chat. "
    "Please use the verified contact section on the CV page."
)

# Keep enough un-emitted trailing context to detect a phone/contact target that
# is split across provider chunks before any protected fragment reaches the
# browser. Phone-like candidates are intentionally bounded well below this.
STREAM_HOLD_CHARS = 96

_TEL_URI_RE = re.compile(r"(?i)\btel\s*:")
_WA_ME_RE = re.compile(r"(?i)\b(?:https?://)?(?:www\.)?wa\.me\s*/\s*\+?[0-9]")
_PHONE_CANDIDATE_RE = re.compile(
    r"(?<![\w@])\+?\d(?:[\t ()/\-]*\d){6,14}(?!\d)"
)
_DATE_LIKE_RE = re.compile(
    r"^(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})$"
)


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _runtime_phone_digits(values: Iterable[str]) -> frozenset[str]:
    normalized: set[str] = set()
    for value in values:
        if not value:
            continue
        digits = _digits(value)
        if 7 <= len(digits) <= 15:
            normalized.add(digits)
    return frozenset(normalized)


class ProtectedContactPolicy:
    """Fail closed on phone/direct-WhatsApp output without logging secrets."""

    def __init__(self, *runtime_phone_values: str) -> None:
        self._runtime_phone_digits = _runtime_phone_digits(runtime_phone_values)

    def contains_protected_contact(self, text: str) -> bool:
        if not text:
            return False
        if _TEL_URI_RE.search(text) or _WA_ME_RE.search(text):
            return True

        for match in _PHONE_CANDIDATE_RE.finditer(text):
            candidate = match.group(0).strip()
            if _DATE_LIKE_RE.fullmatch(candidate):
                continue
            digits = _digits(candidate)
            if not 7 <= len(digits) <= 15:
                continue
            # A plausible phone-shaped sequence is blocked even when it is not
            # the configured number; this also prevents model hallucinations.
            if digits in self._runtime_phone_digits or digits:
                return True
        return False


class ProtectedContactStreamGuard:
    """Stream safe text while retaining enough tail for cross-chunk checks."""

    def __init__(
        self,
        policy: ProtectedContactPolicy,
        *,
        hold_chars: int = STREAM_HOLD_CHARS,
    ) -> None:
        if hold_chars < 32:
            raise ValueError("hold_chars is too small for contact safety")
        self.policy = policy
        self.hold_chars = hold_chars
        self.pending = ""
        self.blocked = False

    def feed(self, chunk: str) -> list[str]:
        if self.blocked or not chunk:
            return []
        self.pending += chunk
        if self.policy.contains_protected_contact(self.pending):
            self.pending = ""
            self.blocked = True
            return [BLOCKED_CONTACT_REPLY]
        if len(self.pending) <= self.hold_chars:
            return []
        emit = self.pending[:-self.hold_chars]
        self.pending = self.pending[-self.hold_chars :]
        return [emit] if emit else []

    def finish(self) -> list[str]:
        if self.blocked:
            return []
        if self.policy.contains_protected_contact(self.pending):
            self.pending = ""
            self.blocked = True
            return [BLOCKED_CONTACT_REPLY]
        emit = self.pending
        self.pending = ""
        return [emit] if emit else []
