from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SMART_DEMO = {
    "en": "Smart-home demo",
    "de": "Smart-Home-Demo",
    "lv": "Viedās mājas demo",
}


class SmartHomeDocumentTitleTests(unittest.TestCase):
    def test_title_updates_from_canonical_translation_on_every_apply(self) -> None:
        source = (ROOT / "frontend" / "smarthome.mjs").read_text(encoding="utf-8")

        self.assertIn("function updateDemoPage({ language, messages })", source)
        self.assertIn("const title = messages?.smart_demo;", source)
        self.assertIn('document.title = `${title} · Andris Rožkalns`;', source)
        self.assertIn(
            "createLanguageController({ onApplied: updateDemoPage })",
            source,
        )
        self.assertIn("toLocaleDateString(localeFor(language)", source)

    def test_smart_demo_translation_is_complete_for_supported_languages(self) -> None:
        for language, expected in EXPECTED_SMART_DEMO.items():
            messages = json.loads(
                (ROOT / "content" / "translations" / f"{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(messages["smart_demo"], expected, language)


if __name__ == "__main__":
    unittest.main()
