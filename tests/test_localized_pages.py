import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "en": ("Junior Technical Support / Linux Operations", "Dortmund, Germany", "/cv.pdf"),
    "de": ("Junior Technical Support / Linux Operations", "Dortmund, Deutschland", "/cv-de.pdf"),
    "lv": ("Junior Technical Support / Linux Operations", "Dortmund, Vācija", "/cv-lv.pdf"),
}
IDENTITY_PATHS = {
    "en": "en/index.html",
    "de": "de/index.html",
    "lv": "lv/index.html",
    "proof_en": "en/proof/index.html",
    "proof_de": "de/proof/index.html",
    "proof_lv": "lv/proof/index.html",
    "lab_en": "en/lab/index.html",
    "lab_de": "de/lab/index.html",
    "lab_lv": "lv/lab/index.html",
    "sitemap": "sitemap.xml",
}


def escape_generated_attribute(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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

            self.assertNotIn('id="chatInput"', document, language)
            self.assertNotIn('id="chatClose"', document, language)
            self.assertIn('id="contactReveal"', document, language)

    def test_homepage_proof_links_keep_the_active_language_without_javascript(self):
        for language in EXPECTED:
            with self.subTest(language=language):
                document = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
                destinations = re.findall(
                    r'<a\b[^>]*\bhref="(/(?:en|de|lv)/proof/(?:#[^"]*)?)"[^>]*>',
                    document,
                )
                self.assertEqual(len(destinations), 4)
                self.assertTrue(
                    all(destination.startswith(f"/{language}/proof/") for destination in destinations),
                    destinations,
                )
                card = re.search(
                    r'<a class="tech-tag github-row" href="([^"]+)" '
                    r'data-local-route="proof/" data-proof-i18n="link_label">',
                    document,
                )
                self.assertIsNotNone(card)
                self.assertEqual(card.group(1), f"/{language}/proof/")

    def test_primary_navigation_links_to_experience_and_education_in_every_locale(self):
        source = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        self.assertIn('href="#experience" data-ui-i18n="v2_nav_experience"', source)
        self.assertIn('href="#education" data-ui-i18n="v2_nav_education"', source)
        responsive = (ROOT / "frontend/styles/v2/responsive.css").read_text(encoding="utf-8")
        self.assertNotIn('.site-nav a[href="#experience"], .site-nav a[href="#education"] { display: none; }', responsive)
        for language in EXPECTED:
            with self.subTest(language=language):
                ui = json.loads((ROOT / "content/ui-v2.json").read_text(encoding="utf-8"))["i18n"][language]
                html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
                nav = re.search(r'<nav class="site-nav"[^>]*>(.*?)</nav>', html, re.DOTALL)
                self.assertIsNotNone(nav)
                links = nav.group(1)
                for section, key in (("experience", "v2_nav_experience"), ("education", "v2_nav_education")):
                    self.assertIn(
                        f'<a href="#{section}" data-ui-i18n="{key}">{ui[key]}</a>',
                        links,
                    )
                    self.assertIn(f'id="{section}"', html)
                self.assertLess(links.index('href="#about"'), links.index('href="#experience"'))
                self.assertLess(links.index('href="#experience"'), links.index('href="#education"'))
                self.assertLess(links.index('href="#education"'), links.index('href="#contact"'))
                self.assertIn('href="#" data-ui-i18n="v2_home"', links)
                self.assertLess(links.index('data-ui-i18n="v2_home"'), links.index('href="#projects"'))
                self.assertIn('aria-controls="siteNavigation"', html)
                self.assertIn('aria-expanded="false"', html)

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
