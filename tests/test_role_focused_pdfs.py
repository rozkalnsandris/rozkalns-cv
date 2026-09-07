from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GENERIC_HASHES = {
    "html/cv.pdf": "a25e3387018003f0788b0c6d4d528eca101a301e83b819d189a5170d7c539be6",
    "html/cv-de.pdf": "ac7bcaa7aefc472d6fd97151de13fb9bb782fada67ec732c598304855f5bfc1b",
    "html/cv-lv.pdf": "fe996d1268d1bdecfc1202a4e2535b0c58bc9e89f9a9f2893bca50619251ab5d",
}
VARIANTS = {
    "devops-en": "html/cv-devops.pdf",
    "devops-de": "html/cv-devops-de.pdf",
    "linux-admin-en": "html/cv-linux-admin.pdf",
    "linux-admin-de": "html/cv-linux-admin-de.pdf",
}


class RoleFocusedPdfTests(unittest.TestCase):
    def test_canonical_profile_exposes_both_role_targets(self) -> None:
        profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        self.assertIn("Junior DevOps", profile["identity"]["career_goal"])
        self.assertIn("Linux Systems Administrator", profile["identity"]["career_goal"])
        de = json.loads((ROOT / "content/translations/de.json").read_text(encoding="utf-8"))
        self.assertIn("Junior DevOps Engineer", de["role"])
        self.assertIn("Linux-Systemadministrator", de["role"])

    def test_generic_pdf_downloads_remain_byte_stable(self) -> None:
        for relative, expected in GENERIC_HASHES.items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_role_variants_are_tracked_by_both_manifests(self) -> None:
        for manifest_name in ("pdf-manifest.json", "pdf-provenance.json"):
            manifest = json.loads((ROOT / "content" / manifest_name).read_text(encoding="utf-8"))
            for case_id, relative in VARIANTS.items():
                self.assertEqual(manifest["pdfs"][case_id]["path"], relative)
                self.assertTrue((ROOT / relative).is_file(), relative)

    def test_variant_generator_uses_ordering_not_new_claims(self) -> None:
        source = (ROOT / "scripts/generate-pdfs.mjs").read_text(encoding="utf-8")
        self.assertIn("profile.identity?.career_goal", source)
        self.assertIn("messages.role", source)
        self.assertIn("reorderItems", source)
        self.assertNotIn("ATS ranking", source)
        self.assertNotIn("hiring probability", source)


if __name__ == "__main__":
    unittest.main()
