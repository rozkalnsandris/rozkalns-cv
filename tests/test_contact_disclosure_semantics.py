from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUTTON = '<button id="contactReveal" class="contact-reveal" type="button" aria-expanded="false" aria-controls="turnstileMount">'


class ContactDisclosureSemanticsTest(unittest.TestCase):
    def test_source_and_generated_html_publish_collapsed_disclosure_contract(self):
        for relative in ("frontend/index.html", "html/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(html.count(BUTTON), 1, relative)
            self.assertEqual(html.count('id="turnstileMount"'), 1, relative)

    def test_contact_controller_synchronizes_expanded_state_with_mount_visibility(self):
        source = (ROOT / "frontend/features/contact.mjs").read_text(encoding="utf-8")
        self.assertIn('function setVerificationExpanded(expanded)', source)
        self.assertIn('mount.hidden = false;\n      setVerificationExpanded(true);', source)
        self.assertGreaterEqual(source.count('setVerificationExpanded(false);'), 2)
        self.assertIn('setVerificationExpanded(!mount.hidden);', source)


if __name__ == "__main__":
    unittest.main()
