from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {
    "technical-support-en":"html/cv-technical-support.pdf",
    "technical-support-de":"html/cv-technical-support-de.pdf",
    "linux-operations-en":"html/cv-linux-operations.pdf",
    "linux-operations-de":"html/cv-linux-operations-de.pdf",
    "application-support-en":"html/cv-application-support.pdf",
    "application-support-de":"html/cv-application-support-de.pdf",
}
RETIRED = ("html/cv-devops.pdf","html/cv-devops-de.pdf","html/cv-linux-admin.pdf","html/cv-linux-admin-de.pdf")

class RoleFocusedPdfTests(unittest.TestCase):
    def test_canonical_profile_uses_support_linux_operations_master(self) -> None:
        profile = json.loads((ROOT/"content/profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["identity"]["role"], "Junior Technical Support / Linux Operations")
        self.assertIn("Application Support", profile["identity"]["career_goal"])
        self.assertNotIn("MLOps", profile["identity"]["career_goal"])

    def test_new_role_variants_are_tracked_by_both_manifests(self) -> None:
        for manifest_name in ("pdf-manifest.json","pdf-provenance.json"):
            manifest = json.loads((ROOT/"content"/manifest_name).read_text(encoding="utf-8"))
            self.assertEqual(set(VARIANTS), set(manifest["pdfs"]) - {"en","de","lv"})
            for case_id, relative in VARIANTS.items():
                self.assertEqual(manifest["pdfs"][case_id]["path"], relative)
                self.assertTrue((ROOT/relative).is_file(), relative)

    def test_devops_first_role_pdfs_are_retired(self) -> None:
        for relative in RETIRED:
            self.assertFalse((ROOT/relative).exists(), relative)

    def test_variant_generator_uses_explicit_truth_preserving_roles(self) -> None:
        source = (ROOT/"scripts/generate-pdfs.mjs").read_text(encoding="utf-8")
        for role in ("Junior Technical Support Engineer","Junior Linux Operations","Application Support Engineer"):
            self.assertIn(role, source)
        self.assertNotIn("variant === 'devops'", source)
        self.assertNotIn("ATS ranking", source)
        self.assertNotIn("hiring probability", source)

if __name__ == "__main__": unittest.main()
