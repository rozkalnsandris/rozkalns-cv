from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {
    "software-testing-en":"html/cv-software-testing.pdf",
    "software-testing-de":"html/cv-software-testing-de.pdf",
    "linux-operations-en":"html/cv-linux-operations.pdf",
    "linux-operations-de":"html/cv-linux-operations-de.pdf",
    "ai-data-quality-en":"html/cv-ai-data-quality.pdf",
    "ai-data-quality-de":"html/cv-ai-data-quality-de.pdf",
}
RETIRED = ("html/cv-devops.pdf","html/cv-devops-de.pdf","html/cv-linux-admin.pdf","html/cv-linux-admin-de.pdf","html/cv-technical-support.pdf","html/cv-technical-support-de.pdf","html/cv-application-support.pdf","html/cv-application-support-de.pdf")

class RoleFocusedPdfTests(unittest.TestCase):
    def test_canonical_profile_uses_qa_linux_data_master(self) -> None:
        profile = json.loads((ROOT/"content/profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["identity"]["role"], "Junior QA / Linux & Internal IT / AI Data Quality")
        self.assertIn("Software Testing / QA", profile["identity"]["career_goal"])
        self.assertIn("AI Data Quality / AI evaluation", profile["identity"]["career_goal"])
        self.assertNotIn("MLOps", profile["identity"]["career_goal"])

    def test_new_role_variants_are_tracked_by_both_manifests(self) -> None:
        for manifest_name in ("pdf-manifest.json","pdf-provenance.json"):
            manifest = json.loads((ROOT/"content"/manifest_name).read_text(encoding="utf-8"))
            self.assertEqual(set(VARIANTS), set(manifest["pdfs"]) - {"en","de","lv"})
            for case_id, relative in VARIANTS.items():
                self.assertEqual(manifest["pdfs"][case_id]["path"], relative)
                self.assertTrue((ROOT/relative).is_file(), relative)

    def test_stale_support_and_devops_role_pdfs_are_retired(self) -> None:
        for relative in RETIRED:
            self.assertFalse((ROOT/relative).exists(), relative)

    def test_variant_generator_uses_explicit_truth_preserving_roles(self) -> None:
        source = (ROOT/"scripts/generate-pdfs.mjs").read_text(encoding="utf-8")
        for role in ("Junior Software Tester / QA","Junior Linux / Internal IT","Junior AI Data Quality / Evaluation"):
            self.assertIn(role, source)
        self.assertNotIn("technical-support", source)
        self.assertNotIn("application-support", source)
        self.assertNotIn("ATS ranking", source)
        self.assertNotIn("hiring probability", source)

if __name__ == "__main__": unittest.main()
