from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "de", "lv")


def alternates(suffix=""):
    return {
        "en": f"https://rozkalns.net/en/{suffix}",
        "de": f"https://rozkalns.net/de/{suffix}",
        "lv": f"https://rozkalns.net/lv/{suffix}",
        "x-default": f"https://rozkalns.net/en/{suffix}",
    }


class SeoCanonicalContractTest(unittest.TestCase):
    def test_root_cv_alias_canonicalizes_to_english_locale(self):
        for relative in ("frontend/index.html", "html/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(html.count('<link rel="canonical" href="https://rozkalns.net/en/">'), 1, relative)
            self.assertEqual(html.count('<meta property="og:url" content="https://rozkalns.net/en/">'), 1, relative)
            if relative.startswith("frontend/"):
                self.assertNotIn('<link rel="alternate" hreflang=', html)

    def test_localized_cv_pages_self_canonicalize(self):
        expected = alternates()
        for language in LANGUAGES:
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(f'<html lang="{language}">', html)
            self.assertEqual(html.count(f'<link rel="canonical" href="{expected[language]}">'), 1)
            self.assertEqual(html.count(f'<meta property="og:url" content="{expected[language]}">'), 1)
            for hreflang, href in expected.items():
                self.assertEqual(html.count(f'<link rel="alternate" hreflang="{hreflang}" href="{href}">'), 1)

    def test_proof_alias_and_localized_routes_use_proof_canonicals(self):
        source = (ROOT / "frontend/proof.html").read_text(encoding="utf-8")
        self.assertEqual(source.count('<link rel="canonical" href="https://rozkalns.net/en/proof/">'), 1)
        expected = alternates("proof/")
        for language in LANGUAGES:
            html = (ROOT / f"html/{language}/proof/index.html").read_text(encoding="utf-8")
            self.assertIn(f'<html lang="{language}">', html)
            self.assertEqual(html.count(f'<link rel="canonical" href="{expected[language]}">'), 1)
            self.assertEqual(html.count(f'<meta property="og:url" content="{expected[language]}">'), 1)
            for hreflang, href in expected.items():
                self.assertEqual(html.count(f'<link rel="alternate" hreflang="{hreflang}" href="{href}">'), 1)

    def test_preview_image_is_crawlable(self):
        robots = (ROOT / "html/robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertNotIn("Disallow: /photo.jpg", robots)


if __name__ == "__main__":
    unittest.main()
