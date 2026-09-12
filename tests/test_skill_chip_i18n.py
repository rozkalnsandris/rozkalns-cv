from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "frontend/index.html"
I18N = ROOT / "frontend/core/i18n.mjs"
TRANSLATIONS = ROOT / "content/translations"
ROW_TO_LIST = {
    "skill_group_linux_operations": "skill_group_linux_operations_items",
    "skill_group_networking_web": "skill_group_networking_web_items",
    "skill_group_containers_monitoring": "skill_group_containers_monitoring_items",
    "skill_group_application_support": "skill_group_application_support_items",
    "skill_group_automation_git": "skill_group_automation_git_items",
}

def translation_items(value: str) -> list[str]:
    return [item.strip() for item in value.split("·")]

def skill_identity(value: str) -> str:
    return re.sub(r"\s*/\s*", "/", value.strip())

def skill_rows() -> dict[str, list[str]]:
    html = INDEX.read_text(encoding="utf-8")
    pattern = re.compile(r'<div class="skill-row"><dt data-i18n="(?P<label>skill_group_[^"]+)">.*?</dt><dd><div class="skill-chips">(?P<chips>.*?)</div></dd></div>')
    chip_pattern = re.compile(r'<span class="skill-chip">([^<]+)</span>')
    return {m.group("label"): chip_pattern.findall(m.group("chips")) for m in pattern.finditer(html)}

class SkillChipI18nTests(unittest.TestCase):
    def test_english_canonical_lists_match_visible_chip_inventory(self) -> None:
        rows = skill_rows()
        self.assertEqual(set(rows), set(ROW_TO_LIST))
        messages = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))
        for row_key, list_key in ROW_TO_LIST.items():
            self.assertEqual([skill_identity(x) for x in translation_items(messages[list_key])], [skill_identity(x) for x in rows[row_key]])

    def test_all_languages_have_complete_skill_lists(self) -> None:
        rows = skill_rows()
        for language in ("en", "de", "lv"):
            messages = json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
            for row_key, list_key in ROW_TO_LIST.items():
                items = translation_items(messages[list_key])
                self.assertEqual(len(items), len(rows[row_key]), f"{language}:{list_key}")
                self.assertTrue(all(items), f"{language}:{list_key}")

    def test_shared_i18n_mapping_fails_closed_before_writing_chips(self) -> None:
        source = I18N.read_text(encoding="utf-8")
        for row_key, list_key in ROW_TO_LIST.items():
            self.assertIn(f'{row_key}: "{list_key}"', source)
        self.assertLess(source.index('if (items.length !== chips.length) return;'), source.index('chips.forEach((chip, index) => {'))

if __name__ == "__main__":
    unittest.main()
