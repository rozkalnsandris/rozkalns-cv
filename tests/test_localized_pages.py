import hashlib
import html as html_lib
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
IDENTITY_PATHS = {
    "en": "en/index.html",
    "de": "de/index.html",
    "lv": "lv/index.html",
    "sitemap": "sitemap.xml",
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

    def test_localized_bound_attributes_keep_keys_and_pretranslated_values(self):
        for language in EXPECTED:
            messages = json.loads(
                (ROOT / f"content/translations/{language}.json").read_text(encoding="utf-8")
            )
            document = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")

            input_match = re.search(r'<input\b(?=[^>]*\bid="chatInput")[^>]*>', document)
            self.assertIsNotNone(input_match, language)
            input_tag = input_match.group(0)
            self.assertIn('data-i18n-placeholder="chat_input"', input_tag, language)
            expected_placeholder = html_lib.escape(messages["chat_input"], quote=True)
            self.assertIn(f'placeholder="{expected_placeholder}"', input_tag, language)

            close_match = re.search(r'<button\b(?=[^>]*\bid="chatClose")[^>]*>', document)
            self.assertIsNotNone(close_match, language)
            close_tag = close_match.group(0)
            self.assertIn('data-i18n-label="chat_close"', close_tag, language)
            expected_label = html_lib.escape(messages["chat_close"], quote=True)
            self.assertIn(f'aria-label="{expected_label}"', close_tag, language)

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

    def test_committed_localized_outputs_match_manifest_identity(self):
        manifest = json.loads((ROOT / "frontend-dist-manifest.json").read_text(encoding="utf-8"))
        localized = manifest.get("_localized")
        self.assertIsInstance(localized, dict)
        self.assertEqual(set(localized), set(IDENTITY_PATHS))
        for name, relative in IDENTITY_PATHS.items():
            row = localized[name]
            self.assertEqual(row["path"], relative)
            payload = (ROOT / "html" / relative).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])

    def test_nginx_static_routing_can_resolve_locale_directories(self):
        nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("index index.html;", nginx)
        self.assertIn("try_files $uri $uri/ =404;", nginx)
        for language in EXPECTED:
            self.assertTrue((ROOT / f"html/{language}/index.html").is_file())


if __name__ == "__main__":
    unittest.main()
