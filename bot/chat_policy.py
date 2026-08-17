from __future__ import annotations

import re
from collections.abc import Iterable


BLOCKED_CONTACT_REPLY = (
    "I can’t provide phone or direct WhatsApp details in chat. "
    "Please use the verified contact section on the CV page."
)

# This small tail is only for short URI-like targets such as tel:/wa.me.
# Phone-shaped suffixes are retained from their actual candidate start, so
# safety does not depend on this fixed tail length.
STREAM_HOLD_CHARS = 96
MAX_UNRESOLVED_PHONE_CHARS = 4096

_TEL_URI_RE = re.compile(r"(?i)\btel\s*:")
_WA_ME_RE = re.compile(r"(?i)\b(?:https?://)?(?:www\.)?wa\s*\.\s*me\s*/\s*\+?[0-9]")
_PHONE_CANDIDATE_RE = re.compile(
    r"(?<![\w@])\+?\d(?:[^\w@]*\d){6,14}(?!\d)"
)
_DATE_LIKE_RE = re.compile(
    r"^(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})$"
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


def _is_phone_candidate_char(character: str) -> bool:
    return character.isdigit() or (
        not character.isalnum() and character not in {"_", "@"}
    )


def _trailing_phone_candidate_start(text: str) -> int:
    """Return the start of an unresolved trailing phone-shaped suffix."""

    index = len(text)
    while index > 0 and _is_phone_candidate_char(text[index - 1]):
        index -= 1
    suffix = text[index:]
    return index if any(character.isdigit() for character in suffix) else len(text)


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
            # Any plausible phone-shaped sequence is blocked, not only the
            # configured value, so a model hallucination cannot bypass policy.
            return True
        return False


class ProtectedContactStreamGuard:
    """Stream safe text while retaining unresolved phone/contact context."""

    def __init__(
        self,
        policy: ProtectedContactPolicy,
        *,
        hold_chars: int = STREAM_HOLD_CHARS,
        max_unresolved_phone_chars: int = MAX_UNRESOLVED_PHONE_CHARS,
    ) -> None:
        if hold_chars < 32:
            raise ValueError("hold_chars is too small for contact safety")
        if max_unresolved_phone_chars < hold_chars:
            raise ValueError("max_unresolved_phone_chars is too small")
        self.policy = policy
        self.hold_chars = hold_chars
        self.max_unresolved_phone_chars = max_unresolved_phone_chars
        self.pending = ""
        self.blocked = False

    def _block(self) -> list[str]:
        self.pending = ""
        self.blocked = True
        return [BLOCKED_CONTACT_REPLY]

    def feed(self, chunk: str) -> list[str]:
        if self.blocked or not chunk:
            return []
        self.pending += chunk
        if self.policy.contains_protected_contact(self.pending):
            return self._block()

        candidate_start = _trailing_phone_candidate_start(self.pending)
        unresolved_length = len(self.pending) - candidate_start
        if unresolved_length > self.max_unresolved_phone_chars:
            # An unresolved phone-shaped suffix may not be emitted merely to
            # satisfy streaming. Fail closed instead of introducing a leak.
            return self._block()

        keep_from = min(
            max(0, len(self.pending) - self.hold_chars),
            candidate_start,
        )
        if keep_from <= 0:
            return []
        emit = self.pending[:keep_from]
        self.pending = self.pending[keep_from:]
        return [emit] if emit else []

    def finish(self) -> list[str]:
        if self.blocked:
            return []
        if self.policy.contains_protected_contact(self.pending):
            return self._block()
        emit = self.pending
        self.pending = ""
        return [emit] if emit else []
