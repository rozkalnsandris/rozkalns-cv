import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_pdfs", ROOT / "scripts" / "check-pdfs.py")
CHECK_PDFS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CHECK_PDFS)


class PdfLinkContractTests(unittest.TestCase):
    TARGETS = ("mailto:public@example.test", "https://github.com/example", "https://example.test/")

    def test_exact_public_link_targets_are_accepted(self) -> None:
        raw = " ".join(f"/Subtype /Link /S /URI /URI ({target})" for target in self.TARGETS)
        CHECK_PDFS.assert_pdf_link_targets("en", raw, self.TARGETS)

    def test_missing_or_protected_link_targets_fail_closed(self) -> None:
        raw = " ".join(f"/Subtype /Link /S /URI /URI ({target})" for target in self.TARGETS[:2])
        with self.assertRaises(CHECK_PDFS.PdfCheckError):
            CHECK_PDFS.assert_pdf_link_targets("en", raw, self.TARGETS)
        raw = " ".join(f"/Subtype /Link /S /URI /URI ({target})" for target in (*self.TARGETS, "tel:+123456"))
        with self.assertRaises(CHECK_PDFS.PdfCheckError):
            CHECK_PDFS.assert_pdf_link_targets("en", raw, self.TARGETS)
