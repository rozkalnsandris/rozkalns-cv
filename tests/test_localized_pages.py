import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "en": ("Junior DevOps &amp; Linux Engineer", "Dortmund, Germany", "/cv.pdf"),
    "de": ("Junior DevOps- &amp; Linux-Engineer", "Dortmund, Deutschland", "/cv-de.pdf"),
    "lv": ("Junior DevOps un Linux inženieris", "Dortmund, Vācija", "/cv-lv.pdf"),
}


class LocalizedPageContractTests(unittest.TestCase):
    def test_localized_html_is_pretranslated_before_javascript(self):
        for language, (role, location, pdf) in EXPECTED.items():
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(f'<html lang="{language}">', html)
            self.assertIn(f'data-i18n="role">{role}</p>', html)
            self.assertRegex(html, rf'id="profileLocation"[^>]*>{re.escape(location)}</span>')
            self.assertRegex(html, rf'id="pdfLink" href="{re.escape(pdf)}"')
            self.assertIn(f'data-lang="{language}" aria-label=', html)
            current = re.findall(r'<a[^>]+data-lang="([^"]+)"[^>]+aria-current="page"', html)
            self.assertEqual(current, [language])

    def test_root_alias_is_english_but_not_a_sitemap_canonical(self):
        root_html = (ROOT / "html/index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="en">', root_html)
        self.assertIn('<link rel="canonical" href="https://rozkalns.net/en/">', root_html)
        sitemap = (ROOT / "html/sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("<loc>https://rozkalns.net/</loc>", sitemap)

    def test_translation_documents_remain_single_source_of_visible_copy(self):
        for language in EXPECTED:
            messages = json.loads((ROOT / f"content/translations/{language}.json").read_text(encoding="utf-8"))
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(messages["tagline"].replace("&", "&amp;"), html)
            self.assertIn(messages["about_p1"].replace("&", "&amp;"), html)


if __name__ == "__main__":
    unittest.main()
