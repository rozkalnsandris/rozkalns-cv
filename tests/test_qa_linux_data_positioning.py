from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QaLinuxDataPositioningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        self.translations = {
            lang: json.loads((ROOT / f"content/translations/{lang}.json").read_text(encoding="utf-8"))
            for lang in ("en", "de", "lv")
        }

    def test_master_identity_is_qa_linux_internal_it_and_data_quality(self) -> None:
        identity = self.profile["identity"]
        self.assertEqual(identity["role"], "Junior QA / Linux & Internal IT / AI Data Quality")
        for target in ("Software Testing / QA", "Linux / Internal IT", "AI Data Quality / AI evaluation"):
            self.assertIn(target, identity["career_goal"])
        for messages in self.translations.values():
            self.assertEqual(messages["role"], identity["role"])
            self.assertNotIn("Technical Support", messages["role"])
            self.assertNotIn("Application Support", messages["role"])

    def test_testing_claims_are_project_evidence_not_employment_claims(self) -> None:
        en = self.translations["en"]
        self.assertIn("browser regression", en["pdf_profile_summary"].lower())
        self.assertIn("contract", en["pdf_profile_summary"].lower())
        self.assertIn("not professional IT employment", en["pdf_profile_summary"])
        self.assertIn("browser regression tests", en["pdf_p7_desc"])
        self.assertNotIn("professional QA experience", en["pdf_profile_summary"].lower())

    def test_employment_chronology_remains_unchanged(self) -> None:
        rows = self.profile["experience"]
        self.assertEqual(
            [(r["id"], r["start"], r["end"]) for r in rows[:2]],
            [("sonepar", "2024-01", "2026-12"), ("kbs", "2023-07", "2023-12")],
        )
        self.assertEqual(rows[1]["organization"], "KBS")

    def test_future_devops_stack_is_not_current_skill_inventory(self) -> None:
        skills = {item for values in self.profile["skills"].values() for item in values}
        self.assertTrue({"Ansible", "Terraform", "AWS Cloud", "Kubernetes", "Helm"}.isdisjoint(skills))


if __name__ == "__main__":
    unittest.main()
