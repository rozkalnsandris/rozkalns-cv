from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "de", "lv")


class EngineeringProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads((ROOT / "content/proof.json").read_text(encoding="utf-8"))
        cls.profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((ROOT / "content/evidence.json").read_text(encoding="utf-8"))
        cls.skill_labels = json.loads((ROOT / "content/skill-labels.json").read_text(encoding="utf-8"))
        cls.translations = {
            language: json.loads((ROOT / f"content/translations/{language}.json").read_text(encoding="utf-8"))
            for language in LANGUAGES
        }

    def test_config_selects_three_to_five_canonical_evidenced_projects(self) -> None:
        self.assertEqual(self.config["canonical_profile"], "content/profile.json")
        self.assertEqual(self.config["canonical_evidence"], "content/evidence.json")
        self.assertEqual(self.config["canonical_skill_labels"], "content/skill-labels.json")
        selected = self.config["featured_project_ids"]
        self.assertGreaterEqual(len(selected), 3)
        self.assertLessEqual(len(selected), 5)
        self.assertEqual(len(selected), len(set(selected)))
        canonical = {project["id"] for project in self.profile["projects"]}
        self.assertTrue(set(selected).issubset(canonical))
        for project_id in selected:
            self.assertTrue(
                any(project_id in item["project_ids"] for item in self.registry["evidence"].values()),
                project_id,
            )

    def test_localized_static_proof_uses_only_canonical_copy_evidence_and_levels(self) -> None:
        project_by_id = {project["id"]: project for project in self.profile["projects"]}
        english = self.translations["en"]
        title_keys = {
            project_id: next(
                key for key, value in english.items()
                if re.fullmatch(r"p\d+_title", key) and value == project_by_id[project_id]["title"]
            )
            for project_id in self.config["featured_project_ids"]
        }
        canonical_levels = {
            concept: level
            for level, concepts in self.profile["skills"].items()
            for concept in concepts
        }

        for language in LANGUAGES:
            document = (ROOT / f"html/{language}/proof/index.html").read_text(encoding="utf-8")
            self.assertNotIn("<script", document.lower(), language)
            self.assertNotIn("+49", document, language)
            self.assertNotIn("data-engineering-proof-projects></div>", document, language)
            self.assertEqual(
                re.findall(r'data-proof-project-id="([^"]+)"', document),
                self.config["featured_project_ids"],
                language,
            )
            messages = self.translations[language]
            for project_id, title_key in title_keys.items():
                prefix = title_key.removesuffix("_title")
                self.assertIn(escape(messages[title_key], quote=True), document, (language, project_id, "title"))
                self.assertIn(escape(messages[f"{prefix}_desc"], quote=True), document, (language, project_id, "summary"))
                operations_key = f"{prefix}_ops"
                if operations_key in messages:
                    self.assertIn(escape(messages[operations_key], quote=True), document, (language, project_id, "operations"))

            for evidence_id, href in re.findall(
                r'data-proof-evidence-id="([^"]+)"[^>]*href="([^"]+)"', document
            ):
                self.assertIn(evidence_id, self.registry["evidence"])
                self.assertEqual(href, self.registry["evidence"][evidence_id]["url"])

            skill_rows = re.findall(
                r'data-proof-skill="([^"]+)">([^<]+)</span><small class="proof-skill-level" data-proof-level="([^"]+)">([^<]+)</small>',
                document,
            )
            self.assertGreater(len(skill_rows), 0, language)
            for concept, label, level, level_label in skill_rows:
                self.assertEqual(level, canonical_levels[concept])
                self.assertEqual(label, escape(self.skill_labels["labels"][concept][language], quote=True))
                self.assertEqual(level_label, escape(messages[f"skills_{level}"], quote=True))

    def test_main_cv_links_to_localized_proof_without_expanding_project_copy(self) -> None:
        for language in LANGUAGES:
            main = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            label = self.config["i18n"][language]["link_label"]
            self.assertIn(f'id="proofLink" href="/{language}/proof/"', main, language)
            self.assertIn(f'data-proof-i18n="link_label">{escape(label, quote=True)}</a>', main, language)

    def test_proof_canonical_and_reciprocal_hreflang_are_route_specific(self) -> None:
        expected = {
            "en": "https://rozkalns.net/en/proof/",
            "de": "https://rozkalns.net/de/proof/",
            "lv": "https://rozkalns.net/lv/proof/",
            "x-default": "https://rozkalns.net/en/proof/",
        }
        for language in LANGUAGES:
            document = (ROOT / f"html/{language}/proof/index.html").read_text(encoding="utf-8")
            self.assertEqual(document.count(f'<link rel="canonical" href="{expected[language]}">'), 1)
            for hreflang, href in expected.items():
                self.assertEqual(document.count(f'<link rel="alternate" hreflang="{hreflang}" href="{href}">'), 1)
            self.assertIn(f'href="/{language}/" data-proof-i18n="back_cv"', document)


if __name__ == "__main__":
    unittest.main()
