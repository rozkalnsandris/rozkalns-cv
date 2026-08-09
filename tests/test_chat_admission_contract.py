from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ChatAdmissionContractTests(unittest.TestCase):
    def test_runtime_uses_admission_entrypoint(self) -> None:
        dockerfile = (ROOT / "bot/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("chat_admission.py chat_entry.py", dockerfile)
        self.assertIn('"chat_entry:app"', dockerfile)

    def test_chat_wrapper_validates_before_original_chat_and_quota(self) -> None:
        entry = (ROOT / "bot/chat_entry.py").read_text(encoding="utf-8")
        validate = "validate_session(session, client_key, base.CLIENT_KEY_SECRET)"
        original = "return _original_chat()"
        self.assertIn(validate, entry)
        self.assertIn(original, entry)
        self.assertLess(entry.index(validate), entry.index(original))

        app_source = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        self.assertIn("decision = STORE.reserve(client_key)", app_source)

    def test_frontend_uses_distinct_chat_action_and_session_header(self) -> None:
        source = (ROOT / "frontend/features/chat.mjs").read_text(encoding="utf-8")
        self.assertIn('action: "chat_admission"', source)
        self.assertIn('"/api/chat-admission"', source)
        self.assertIn('"X-Chat-Admission": session', source)
        self.assertNotIn('action: "contact_reveal"', source)


if __name__ == "__main__":
    unittest.main()
