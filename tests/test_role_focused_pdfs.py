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

    def test_pdf_checker_projection_has_current_translation_keys(self) -> None:
        import importlib.util
        path = ROOT / "scripts" / "check-pdfs.py"
        spec = importlib.util.spec_from_file_location("cv_pdf_projection_checker", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for language in ("en", "de", "lv"):
            messages = json.loads((ROOT / "content" / "translations" / f"{language}.json").read_text(encoding="utf-8"))
            self.assertFalse(set(module.PDF_TRANSLATION_KEYS) - set(messages))
            self.assertIn("pdf_p7_desc", module.PDF_TRANSLATION_KEYS)
            self.assertNotIn("pdf_p8_desc", module.PDF_TRANSLATION_KEYS)
            self.assertNotIn("ed1_title", module.PDF_TRANSLATION_KEYS)

    def test_legacy_role_pdf_urls_redirect_to_master_pdfs(self) -> None:
        config = (ROOT / "deploy/simple-deploy/nginx.conf").read_text(encoding="utf-8")
        legacy_roles = "(?:devops|linux-admin|technical-support|application-support)"
        static_pdf_location = r"location ~* \.(?:png|jpg|jpeg|svg|woff2?|pdf)$ {"
        self.assertIn(static_pdf_location, config)
        static_pdf_position = config.index(static_pdf_location)

        for suffix, target in (("", "/cv.pdf"), ("-de", "/cv-de.pdf")):
            with self.subTest(suffix=suffix):
                location = rf"location ~ ^/cv-{legacy_roles}{suffix}\.pdf$ {{"
                self.assertIn(location, config)
                location_position = config.index(location)
                next_block = config[location_position + len(location):].split("}", 1)[0]
                self.assertIn(f"return 308 {target};", next_block)
                self.assertIn("absolute_redirect off;", next_block)
                self.assertLess(
                    next_block.index("absolute_redirect off;"),
                    next_block.index(f"return 308 {target};"),
                )
                self.assertLess(location_position, static_pdf_position)

    def test_variant_generator_uses_explicit_truth_preserving_roles(self) -> None:
        source = (ROOT/"scripts/generate-pdfs.mjs").read_text(encoding="utf-8")
        for role in ("Junior Software Tester / QA","Junior Linux / Internal IT","Junior AI Data Quality / Evaluation"):
            self.assertIn(role, source)
        self.assertNotIn("technical-support", source)
        self.assertNotIn("application-support", source)
        self.assertNotIn("ATS ranking", source)
        self.assertNotIn("hiring probability", source)

if __name__ == "__main__": unittest.main()
