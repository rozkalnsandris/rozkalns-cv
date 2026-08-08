from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurrentContactPolicyTests(unittest.TestCase):
    def test_canonical_email_is_public_and_phone_is_runtime_protected(self) -> None:
        profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["contact"]["email"], {"value": "andris@rozkalns.net", "visibility": "public"})
        self.assertEqual(profile["contact"]["phone"], {"visibility": "runtime-protected"})

    def test_assistant_exposes_email_but_not_phone(self) -> None:
        prompt = (ROOT / "bot/system_prompt.txt").read_text(encoding="utf-8")
        self.assertIn("Email: andris@rozkalns.net", prompt)
        self.assertIn("Phone and WhatsApp: available only through", prompt)
        self.assertNotRegex(prompt, r"Phone:\s*\+[0-9]")

    def test_public_frontend_has_no_direct_numbered_contact_target(self) -> None:
        index = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")
        contact = (ROOT / "frontend/features/contact.mjs").read_text(encoding="utf-8")
        self.assertIn("mailto:andris@rozkalns.net", index)
        self.assertIn('searchParams.get("contact") === "whatsapp"', app)
        self.assertNotRegex(index + app + contact, r"https://wa\.me/[0-9]")
        self.assertNotRegex(index + app + contact, r"tel:\+[0-9]")

    def test_bootstrap_keeps_personal_author_fallback_removed(self) -> None:
        bootstrap = (ROOT / "scripts/bootstrap-github.sh").read_text(encoding="utf-8")
        self.assertIn("GIT_AUTHOR_EMAIL", bootstrap)
        self.assertNotRegex(bootstrap, r"GIT_AUTHOR_EMAIL=.*@")
        self.assertNotIn('git config user.email "andris@rozkalns.net"', bootstrap)


if __name__ == "__main__":
    unittest.main()
