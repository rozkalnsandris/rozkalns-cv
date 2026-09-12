from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "de", "lv")
PROFICIENCY_GROUPS = ("core", "working", "learning", "foundations")
PRESENTATION_GROUPS = ("linux_operations", "networking_web", "containers_monitoring", "application_support", "automation_git")
SEPARATOR = " · "

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def validate_skill_consistency(profile, skill_labels, translations) -> None:
    skills = profile.get("skills")
    groups = profile.get("skill_groups")
    if not isinstance(skills, dict) or tuple(skills) != PROFICIENCY_GROUPS:
        raise AssertionError("canonical proficiency groups/order changed")
    if not isinstance(groups, dict) or tuple(groups) != PRESENTATION_GROUPS:
        raise AssertionError("canonical recruiter skill groups/order changed")
    labels = skill_labels.get("labels")
    canonical = [skill for group in PROFICIENCY_GROUPS for skill in skills[group]]
    presented = [skill for group in PRESENTATION_GROUPS for skill in groups[group]]
    if len(canonical) != len(set(canonical)) or set(labels) != set(canonical):
        raise AssertionError("canonical skill labels do not match proficiency concepts")
    if presented != list(dict.fromkeys(presented)) or set(presented) != set(canonical):
        raise AssertionError("recruiter groups must present every canonical skill exactly once")
    for concept in canonical:
        if set(labels[concept]) != set(LANGUAGES):
            raise AssertionError(f"localized label shape is invalid for {concept}")
    for language in LANGUAGES:
        document = translations[language]
        for group in PROFICIENCY_GROUPS:
            expected = SEPARATOR.join(labels[c][language] for c in skills[group])
            if document.get(f"skills_{group}_items") != expected:
                raise AssertionError(f"{language}:skills_{group}_items drift")
        for group in PRESENTATION_GROUPS:
            expected = SEPARATOR.join(labels[c][language] for c in groups[group])
            if document.get(f"skill_group_{group}_items") != expected:
                raise AssertionError(f"{language}:skill_group_{group}_items drift")

class SkillContentConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_json(ROOT / "content/profile.json")
        self.skill_labels = load_json(ROOT / "content/skill-labels.json")
        self.translations = {language: load_json(ROOT / f"content/translations/{language}.json") for language in LANGUAGES}

    def test_localized_skill_groups_match_canonical_profile(self) -> None:
        validate_skill_consistency(self.profile, self.skill_labels, self.translations)

    def test_foundations_match_current_public_fact_set(self) -> None:
        self.assertEqual(self.profile["skills"]["foundations"], ["Networking", "SSH/FTP", "HTML/CSS"])

    def test_future_devops_tooling_is_not_prominent(self) -> None:
        flattened = {skill for values in self.profile["skills"].values() for skill in values}
        self.assertTrue({"Ansible", "Terraform", "AWS Cloud"}.isdisjoint(flattened))
        self.assertEqual(self.profile["skills"]["learning"], ["Basic SQL"])

    def test_presentation_membership_change_fails_closed(self) -> None:
        profile = deepcopy(self.profile)
        profile["skill_groups"]["automation_git"].append("Networking")
        with self.assertRaises(AssertionError):
            validate_skill_consistency(profile, self.skill_labels, self.translations)

if __name__ == "__main__":
    unittest.main()
