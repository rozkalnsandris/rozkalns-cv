from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from chat_policy import (  # noqa: E402
    BLOCKED_CONTACT_REPLY,
    ProtectedContactPolicy,
    ProtectedContactStreamGuard,
)


class ProtectedContactPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ProtectedContactPolicy(
            "+49 170 1234567",
            "tel:+491701234567",
        )

    def test_blocks_phone_like_variants(self) -> None:
        blocked = (
            "+49 170 1234567",
            "+49-170-1234567",
            "+49 (170) 1234567",
            "491701234567",
            "tel:+491701234567",
            "https://wa.me/491701234567",
            "wa.me/+491701234567",
        )
        for value in blocked:
            with self.subTest(value=value):
                self.assertTrue(self.policy.contains_protected_contact(value))

    def test_blocks_hallucinated_plausible_phone_number(self) -> None:
        self.assertTrue(
            self.policy.contains_protected_contact("Call me on +49 151 7654321")
        )

    def test_allows_public_email_years_and_versions(self) -> None:
        allowed = (
            "Email Andris at andris@rozkalns.net.",
            "Available from 2027-01.",
            "Python 3.13 and Docker 29.1.2 are relevant examples.",
            "The audit date is 2026-08-08.",
        )
        for value in allowed:
            with self.subTest(value=value):
                self.assertFalse(self.policy.contains_protected_contact(value))

    def test_cross_chunk_phone_never_emits_before_block(self) -> None:
        guard = ProtectedContactStreamGuard(self.policy)
        emitted: list[str] = []
        emitted.extend(guard.feed("For WhatsApp use +49 170 "))
        emitted.extend(guard.feed("123"))
        emitted.extend(guard.feed("4567 now"))
        emitted.extend(guard.finish())
        self.assertEqual(emitted, [BLOCKED_CONTACT_REPLY])
        self.assertNotIn("1234567", "".join(emitted))

    def test_safe_long_stream_still_streams_before_finish(self) -> None:
        guard = ProtectedContactStreamGuard(self.policy)
        first = guard.feed("A" * 140)
        self.assertEqual(first, ["A" * 44])
        final = guard.finish()
        self.assertEqual(first + final, ["A" * 44, "A" * 96])

    def test_direct_whatsapp_target_split_across_chunks_is_blocked(self) -> None:
        guard = ProtectedContactStreamGuard(self.policy)
        emitted: list[str] = []
        emitted.extend(guard.feed("Open https://wa."))
        emitted.extend(guard.feed("me/49170"))
        emitted.extend(guard.feed("1234567"))
        emitted.extend(guard.finish())
        self.assertEqual(emitted, [BLOCKED_CONTACT_REPLY])


if __name__ == "__main__":
    unittest.main()
