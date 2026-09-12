from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SupportLinuxOpsPositioningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        self.translations = {lang: json.loads((ROOT / f"content/translations/{lang}.json").read_text(encoding="utf-8")) for lang in ("en","de","lv")}

    def test_master_identity_is_support_linux_operations(self) -> None:
        self.assertEqual(self.profile["identity"]["role"], "Junior Technical Support / Linux Operations")
        self.assertNotIn("MLOps", self.profile["identity"]["career_goal"])
        for messages in self.translations.values():
            self.assertEqual(messages["role"], "Junior Technical Support / Linux Operations")
            self.assertNotIn("DevOps Engineer", messages["role"])
            self.assertNotIn("SRE", messages["role"])

    def test_employment_chronology_separates_kbs_and_sonepar(self) -> None:
        rows = self.profile["experience"]
        self.assertEqual([(r["id"], r["start"], r["end"]) for r in rows[:2]], [("sonepar","2024-01","2026-12"),("kbs","2023-07","2023-12")])
        self.assertEqual(rows[1]["organization"], "KBS")

    def test_linux_operations_lab_is_flagship_but_not_fake_completed_work(self) -> None:
        self.assertEqual(self.profile["projects"][0]["id"], "linux-ops-lab")
        en = self.translations["en"]
        self.assertIn("14 Sep", en["p8_desc"])
        self.assertIn("published only when they exist", en["p8_ops"])
        for forbidden in ("10 documented incidents completed", "5 runbooks completed", "production incident portfolio"):
            self.assertNotIn(forbidden, en["p8_desc"] + en["p8_ops"])

    def test_future_devops_stack_is_not_current_skill_inventory(self) -> None:
        skills = {item for values in self.profile["skills"].values() for item in values}
        self.assertTrue({"Ansible", "Terraform", "AWS Cloud", "Kubernetes", "Helm"}.isdisjoint(skills))

if __name__ == "__main__":
    unittest.main()
