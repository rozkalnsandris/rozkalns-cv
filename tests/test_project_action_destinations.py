"""Regression for six featured project destinations after #549."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CARD = re.compile(
    r'<article class="project-entry primary project-card"[^>]*data-project-slug="([^"]+)"[^>]*>(.*?)</article>',
    re.DOTALL,
)
EXPECTED_SOURCES = {
    "hermes-tech": "https://github.com/rozkalnsandris/hermes-tech",
    "hermes-deals": "https://github.com/rozkalnsandris/hermes-deals",
    "weather": "https://github.com/rozkalnsandris/rozkalns_weather",
    "coloring-pages": "https://github.com/rozkalnsandris/coloring-pages",
    "cv-platform": "https://github.com/rozkalnsandris/rozkalns-cv",
    "homelab": "https://github.com/rozkalnsandris/RPi5_main",
}
PUBLIC_LIVE = {
    "hermes-tech": "https://tech.rozkalns.net/",
    "coloring-pages": "https://ausmalwiese.de/",
    "cv-platform": "https://rozkalns.net/",
}


class ProjectActionDestinationsTests(unittest.TestCase):
    def check_cards(self, document: str, language: str) -> None:
        cards = dict(CARD.findall(document))
        self.assertEqual(tuple(cards), tuple(EXPECTED_SOURCES))
        for slug, source in EXPECTED_SOURCES.items():
            with self.subTest(slug=slug):
                self.assertIn(f'href="{source}" rel="external"', cards[slug])
        for slug, live in PUBLIC_LIVE.items():
            with self.subTest(slug=slug):
                self.assertIn(f'href="{live}" rel="external"', cards[slug])
        self.assertIn('href="https://deals.rozkalns.net/" rel="external"', cards["hermes-deals"])
        self.assertNotIn("weather.rozkalns.net", cards["weather"])
        self.assertIn(
            f'href="/{language}/proof/#homelab" data-local-route="proof/#homelab"',
            cards["homelab"],
        )
        self.assertIn(
            f'href="/{language}/proof/" data-local-route="proof/" data-proof-i18n="link_label"',
            cards["cv-platform"],
        )
        self.assertNotIn('target="_blank"', "".join(cards.values()))

    def test_source_labels(self):
        self.check_cards((ROOT / "frontend/index.html").read_text(encoding="utf-8"), "en")

    def test_localized_no_js_routes_and_deep_links(self):
        for language in ("en", "de", "lv"):
            with self.subTest(language=language):
                page = (ROOT / "html" / language / "index.html").read_text(encoding="utf-8")
                self.check_cards(page, language)
                proof = (ROOT / "html" / language / "proof" / "index.html").read_text(encoding="utf-8")
                self.assertIn('id="homelab" data-proof-project-id="homelab"', proof)


if __name__ == "__main__":
    unittest.main()
