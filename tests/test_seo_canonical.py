from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ALTERNATES = {
    "en": "https://rozkalns.net/en/",
    "de": "https://rozkalns.net/de/",
    "lv": "https://rozkalns.net/lv/",
    "x-default": "https://rozkalns.net/en/",
}


class SeoCanonicalContractTest(unittest.TestCase):
    def test_root_alias_canonicalizes_to_english_locale(self):
        for relative in ("frontend/index.html", "html/index.html"):
            html = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(
                html.count('<link rel="canonical" href="https://rozkalns.net/en/">'),
                1,
                relative,
            )
            self.assertEqual(
                html.count('<meta property="og:url" content="https://rozkalns.net/en/">'),
                1,
                relative,
            )
            self.assertNotIn('<link rel="alternate" hreflang=', html)

    def test_localized_pages_self_canonicalize_and_publish_reciprocal_hreflang(self):
        for language in ("en", "de", "lv"):
            html = (ROOT / f"html/{language}/index.html").read_text(encoding="utf-8")
            self.assertIn(f'<html lang="{language}">', html)
            self.assertEqual(
                html.count(f'<link rel="canonical" href="https://rozkalns.net/{language}/">'),
                1,
            )
            self.assertEqual(
                html.count(f'<meta property="og:url" content="https://rozkalns.net/{language}/">'),
                1,
            )
            for alternate, href in ALTERNATES.items():
                self.assertEqual(
                    html.count(f'<link rel="alternate" hreflang="{alternate}" href="{href}">'),
                    1,
                )
            self.assertIn(f'href="/{language}/" data-lang="{language}"', html)
            self.assertIn(f'data-lang="{language}" aria-label=', html)

    def test_preview_image_is_crawlable(self):
        robots = (ROOT / "html/robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertNotIn("Disallow: /photo.jpg", robots)


if __name__ == "__main__":
    unittest.main()
