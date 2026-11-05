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
LANGUAGES = ("en", "de", "lv")


def alternates(suffix=""):
    return {
        "en": f"https://rozkalns.net/en/{suffix}",
        "de": f"https://rozkalns.net/de/{suffix}",
        "lv": f"https://rozkalns.net/lv/{suffix}",
        "x-default": f"https://rozkalns.net/en/{suffix}",
    }


class SitemapContractTests(unittest.TestCase):
    def test_sitemap_contains_cv_and_proof_locales_with_route_specific_alternates(self):
        root = ET.parse(SITEMAP).getroot()
        self.assertEqual(root.tag, f"{{{NS['sm']}}}urlset")
        urls = root.findall("sm:url", NS)
        expected_rows = [
            *(f"https://rozkalns.net/{language}/" for language in LANGUAGES),
            *(f"https://rozkalns.net/{language}/proof/" for language in LANGUAGES),
        ]
        self.assertEqual([url.find("sm:loc", NS).text for url in urls], expected_rows)
        for url in urls:
            location = url.find("sm:loc", NS).text
            expected = alternates("proof/" if "/proof/" in location else "")
            actual = {
                link.attrib["hreflang"]: link.attrib["href"]
                for link in url.findall("xhtml:link", NS)
            }
            self.assertEqual(actual, expected)
        xml = SITEMAP.read_text(encoding="utf-8")
        self.assertNotIn("<loc>https://rozkalns.net/</loc>", xml)
        self.assertNotIn("<loc>https://rozkalns.net/proof.html</loc>", xml)
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
