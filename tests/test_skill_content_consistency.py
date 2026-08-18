from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "de", "lv")
GROUPS = ("core", "working", "learning", "foundations")
SEPARATOR = " · "


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_skill_consistency(profile, skill_labels, translations) -> None:
    skills = profile.get("skills")
    if not isinstance(skills, dict) or tuple(skills) != GROUPS:
        raise AssertionError("canonical skill groups/order changed")

    label_document = skill_labels
    if not isinstance(label_document, dict) or set(label_document) != {
        "schema_version",
        "labels",
    }:
        raise AssertionError("skill label document shape is invalid")
    if label_document["schema_version"] != 1:
        raise AssertionError("skill label schema version is invalid")

    labels = label_document["labels"]
    if not isinstance(labels, dict):
        raise AssertionError("skill labels must be an object")

    canonical_items: list[str] = []
    for group in GROUPS:
        items = skills.get(group)
        if not isinstance(items, list) or not items:
            raise AssertionError(f"profile.skills.{group} must be non-empty")
        if any(not isinstance(item, str) or not item.strip() for item in items):
            raise AssertionError(f"profile.skills.{group} contains invalid items")
        canonical_items.extend(items)

    if len(set(canonical_items)) != len(canonical_items):
        raise AssertionError("canonical skill concepts must be unique across groups")
    if set(labels) != set(canonical_items):
        raise AssertionError("skill label concepts do not match canonical profile")

    for concept in canonical_items:
        localized = labels[concept]
        if not isinstance(localized, dict) or set(localized) != set(LANGUAGES):
            raise AssertionError(f"localized label shape is invalid for {concept}")
        if any(
            not isinstance(localized[language], str)
            or not localized[language].strip()
            for language in LANGUAGES
        ):
            raise AssertionError(f"localized label is invalid for {concept}")

    if set(translations) != set(LANGUAGES):
        raise AssertionError("translation languages do not match contract")

    for language in LANGUAGES:
        document = translations[language]
        for group in GROUPS:
            key = f"skills_{group}_items"
            expected = SEPARATOR.join(
                labels[concept][language] for concept in skills[group]
            )
            if document.get(key) != expected:
                raise AssertionError(
                    f"{language}:{key} does not match canonical skill membership/order"
                )


class SkillContentConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_json(ROOT / "content" / "profile.json")
        self.skill_labels = load_json(ROOT / "content" / "skill-labels.json")
        self.translations = {
            language: load_json(
                ROOT / "content" / "translations" / f"{language}.json"
            )
            for language in LANGUAGES
        }

    def test_localized_skill_groups_match_canonical_profile(self) -> None:
        validate_skill_consistency(
            self.profile,
            self.skill_labels,
            self.translations,
        )

    def test_foundations_match_owner_approved_fact_set(self) -> None:
        self.assertEqual(
            self.profile["skills"]["foundations"],
            ["Networking", "SSH/FTP", "PHP/IPB forums", "HTML/CSS"],
        )

    def test_localized_addition_fails_closed(self) -> None:
        translations = deepcopy(self.translations)
        translations["de"]["skills_foundations_items"] += " · Extra"
        with self.assertRaises(AssertionError):
            validate_skill_consistency(self.profile, self.skill_labels, translations)

    def test_localized_removal_fails_closed(self) -> None:
        translations = deepcopy(self.translations)
        translations["lv"]["skills_foundations_items"] = " · ".join(
            translations["lv"]["skills_foundations_items"].split(" · ")[:-1]
        )
        with self.assertRaises(AssertionError):
            validate_skill_consistency(self.profile, self.skill_labels, translations)

    def test_localized_reordering_fails_closed(self) -> None:
        translations = deepcopy(self.translations)
        items = translations["en"]["skills_foundations_items"].split(" · ")
        items[0], items[1] = items[1], items[0]
        translations["en"]["skills_foundations_items"] = " · ".join(items)
        with self.assertRaises(AssertionError):
            validate_skill_consistency(self.profile, self.skill_labels, translations)

    def test_canonical_membership_change_requires_label_mapping(self) -> None:
        profile = deepcopy(self.profile)
        profile["skills"]["foundations"].append("Unmapped skill")
        with self.assertRaises(AssertionError):
            validate_skill_consistency(profile, self.skill_labels, self.translations)


if __name__ == "__main__":
    unittest.main()
