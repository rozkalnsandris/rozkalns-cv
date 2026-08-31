from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TITLES = {
    "en": "Andris Rožkalns · DevOps & Linux Engineer",
    "de": "Andris Rožkalns · DevOps Engineer / Linux-Systemadministrator",
    "lv": "Andris Rožkalns · DevOps un Linux inženieris",
}


class MainDocumentTitleTests(unittest.TestCase):
    def test_main_title_uses_url_owned_initial_language_apply(self) -> None:
        source = (ROOT / "frontend" / "app.mjs").read_text(encoding="utf-8")
        self.assertIn("export function updateMainDocumentTitle({ messages }", source)
        self.assertIn("const role = messages?.role;", source)
        self.assertIn('role.startsWith("Junior ")', source)
        self.assertIn('documentLike.title = `Andris Rožkalns · ${titleRole}`;', source)
        self.assertIn("onApplied(state) {", source)
        self.assertIn("updateMainDocumentTitle(state);", source)
        self.assertIn("syncChatLauncher(state.messages);", source)
        self.assertLess(
            source.index("updateMainDocumentTitle(state);"),
            source.index("syncChatLauncher(state.messages);"),
        )
        self.assertIn("initialLanguage: document.documentElement.lang", source)
        self.assertIn("await languageController.tryApply(languageController.language);", source)

    def test_existing_role_translation_derives_expected_title_in_every_language(self) -> None:
        for language, expected in EXPECTED_TITLES.items():
            messages = json.loads(
                (ROOT / "content" / "translations" / f"{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            role = messages["role"]
            self.assertTrue(role.startswith("Junior "), language)
            self.assertEqual(f"Andris Rožkalns · {role.removeprefix('Junior ').strip()}", expected, language)


if __name__ == "__main__":
    unittest.main()
