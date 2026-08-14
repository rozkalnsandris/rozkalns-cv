from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "frontend" / "index.html"
I18N = ROOT / "frontend" / "core" / "i18n.mjs"
TRANSLATIONS = ROOT / "content" / "translations"

ROW_TO_LIST = {
    "skills_core": "skills_core_items",
    "skills_working": "skills_working_items",
    "skills_learning": "skills_learning_items",
    "skills_foundations": "skills_foundations_items",
}


def translation_items(value: str) -> list[str]:
    return [item.strip() for item in value.split("·")]


def skill_identity(value: str) -> str:
    return re.sub(r"\s*/\s*", "/", value.strip())


def skill_rows() -> dict[str, list[str]]:
    html = INDEX.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<div class="skill-row"><dt data-i18n="(?P<label>skills_[^"]+)">.*?</dt>'
        r'<dd><div class="skill-chips">(?P<chips>.*?)</div></dd></div>'
    )
    chip_pattern = re.compile(r'<span class="skill-chip">([^<]+)</span>')
    rows: dict[str, list[str]] = {}
    for match in pattern.finditer(html):
        rows[match.group("label")] = chip_pattern.findall(match.group("chips"))
    return rows


class SkillChipI18nTests(unittest.TestCase):
    def test_english_canonical_lists_match_visible_chip_inventory(self) -> None:
        rows = skill_rows()
        self.assertEqual(set(rows), set(ROW_TO_LIST))

        messages = json.loads(
            (TRANSLATIONS / "en.json").read_text(encoding="utf-8")
        )
        for row_key, list_key in ROW_TO_LIST.items():
            canonical = [skill_identity(item) for item in translation_items(messages[list_key])]
            visible = [skill_identity(item) for item in rows[row_key]]
            self.assertEqual(canonical, visible)

    def test_all_languages_have_complete_skill_lists(self) -> None:
        rows = skill_rows()
        for language in ("en", "de", "lv"):
            messages = json.loads(
                (TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8")
            )
            for row_key, list_key in ROW_TO_LIST.items():
                items = translation_items(messages[list_key])
                self.assertEqual(len(items), len(rows[row_key]), f"{language}:{list_key}")
                self.assertTrue(all(items), f"{language}:{list_key}")

        de = json.loads((TRANSLATIONS / "de.json").read_text(encoding="utf-8"))
        lv = json.loads((TRANSLATIONS / "lv.json").read_text(encoding="utf-8"))
        self.assertEqual(translation_items(de["skills_core_items"])[0], "Linux-Administration")
        self.assertEqual(translation_items(de["skills_foundations_items"])[0], "Netzwerke")
        self.assertEqual(translation_items(lv["skills_core_items"])[0], "Linux administrēšana")
        self.assertEqual(translation_items(lv["skills_foundations_items"])[0], "Tīklošana")

    def test_shared_i18n_mapping_fails_closed_before_writing_chips(self) -> None:
        source = I18N.read_text(encoding="utf-8")
        for row_key, list_key in ROW_TO_LIST.items():
            self.assertIn(f'{row_key}: "{list_key}"', source)

        mismatch = 'if (items.length !== chips.length) return;'
        write = "chips.forEach((chip, index) => {"
        self.assertIn(mismatch, source)
        self.assertIn(write, source)
        self.assertLess(source.index(mismatch), source.index(write))
        self.assertIn("applySkillTranslations(messages, { root });", source)


if __name__ == "__main__":
    unittest.main()
