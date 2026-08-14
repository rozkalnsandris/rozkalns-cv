from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ContactPreloadI18nTests(unittest.TestCase):
    def test_contact_controls_use_core_i18n_before_lazy_module_loads(self) -> None:
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")

        self.assertIn(
            'id="contactPhone" class="contact-masked" '
            'data-i18n-label="contact_phone_hidden"',
            html,
        )
        self.assertIn(
            'class="contact-reveal-label" data-i18n="contact_reveal"',
            html,
        )

    def test_contact_preload_translation_keys_are_complete(self) -> None:
        for language in ("en", "de", "lv"):
            path = ROOT / "content" / "translations" / f"{language}.json"
            messages = json.loads(path.read_text(encoding="utf-8"))
            for key in ("contact_reveal", "contact_phone_hidden"):
                self.assertIsInstance(messages.get(key), str, f"{language}:{key}")
                self.assertTrue(messages[key].strip(), f"{language}:{key}")


if __name__ == "__main__":
    unittest.main()
