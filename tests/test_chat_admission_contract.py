from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ChatAdmissionContractTests(unittest.TestCase):
    def test_runtime_uses_factory_entrypoint(self) -> None:
        dockerfile = (ROOT / "bot/Dockerfile").read_text(encoding="utf-8")
        self.assertIn("chat_admission.py chat_entry.py", dockerfile)
        self.assertIn('"chat_entry:create_app()"', dockerfile)

        entry = (ROOT / "bot/chat_entry.py").read_text(encoding="utf-8")
        self.assertIn("from app import close_app_services, create_app as create_base_app", entry)
        self.assertIn("app = create_base_app()", entry)
        self.assertIn("atexit.register(close_app_services, app)", entry)

    def test_factory_validates_admission_before_quota(self) -> None:
        app_source = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        validate = "validate_session(session, client_key, active.client_key_secret)"
        reserve = "decision = active_store.reserve(client_key)"
        self.assertIn(validate, app_source)
        self.assertIn(reserve, app_source)
        self.assertLess(app_source.index(validate), app_source.index(reserve))
        self.assertNotIn('app.view_functions["chat"]', app_source)

    def test_frontend_uses_distinct_chat_action_and_session_header(self) -> None:
        source = (ROOT / "frontend/features/chat.mjs").read_text(encoding="utf-8")
        self.assertIn('action: "chat_admission"', source)
        self.assertIn('"/api/chat-admission"', source)
        self.assertIn('"X-Chat-Admission": session', source)
        self.assertNotIn('action: "contact_reveal"', source)


if __name__ == "__main__":
    unittest.main()
