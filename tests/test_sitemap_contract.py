import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "html" / "sitemap.xml"
ROBOTS = ROOT / "html" / "robots.txt"
INDEX = ROOT / "frontend" / "index.html"
SMARTHOME = ROOT / "html" / "smarthome.html"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class SitemapContractTests(unittest.TestCase):
    def test_sitemap_contains_only_the_public_canonical_url(self):
        root = ET.parse(SITEMAP).getroot()
        self.assertEqual(root.tag, f"{{{NS['sm']}}}urlset")
        locations = [
            node.text for node in root.findall("sm:url/sm:loc", NS) if node.text
        ]
        self.assertEqual(locations, ["https://rozkalns.net/"])

        index = INDEX.read_text(encoding="utf-8")
        canonical = re.findall(
            r'<link rel="canonical" href="([^"]+)">', index
        )
        self.assertEqual(canonical, locations)

        xml = SITEMAP.read_text(encoding="utf-8")
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
