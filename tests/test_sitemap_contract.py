import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "html" / "sitemap.xml"
ROBOTS = ROOT / "html" / "robots.txt"
SMARTHOME = ROOT / "html" / "smarthome.html"
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}
EXPECTED = {
    "en": "https://rozkalns.net/en/",
    "de": "https://rozkalns.net/de/",
    "lv": "https://rozkalns.net/lv/",
    "x-default": "https://rozkalns.net/en/",
}


class SitemapContractTests(unittest.TestCase):
    def test_sitemap_contains_canonical_locales_with_reciprocal_alternates(self):
        root = ET.parse(SITEMAP).getroot()
        self.assertEqual(root.tag, f"{{{NS['sm']}}}urlset")
        urls = root.findall("sm:url", NS)
        self.assertEqual(
            [url.find("sm:loc", NS).text for url in urls],
            [EXPECTED["en"], EXPECTED["de"], EXPECTED["lv"]],
        )
        for url in urls:
            alternates = {
                link.attrib["hreflang"]: link.attrib["href"]
                for link in url.findall("xhtml:link", NS)
            }
            self.assertEqual(alternates, EXPECTED)
        xml = SITEMAP.read_text(encoding="utf-8")
        self.assertNotIn("<loc>https://rozkalns.net/</loc>", xml)
        self.assertNotIn("<priority>", xml)
        self.assertNotIn("<changefreq>", xml)
        self.assertNotIn("<lastmod>", xml)

    def test_robots_advertises_sitemap_and_noindex_demo_stays_excluded(self):
        robots = ROBOTS.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            [line for line in robots if line.lower().startswith("sitemap:")],
            ["Sitemap: https://rozkalns.net/sitemap.xml"],
        )
        smarthome = SMARTHOME.read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex">', smarthome)
        self.assertNotIn("smarthome.html", SITEMAP.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
