import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RE = re.compile(
    r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL
)


def load_person(relative):
    html = (ROOT / relative).read_text(encoding="utf-8")
    matches = SCRIPT_RE.findall(html)
    if len(matches) != 1:
        raise AssertionError(
            f"{relative}: expected exactly one JSON-LD script, got {len(matches)}"
        )
    return json.loads(matches[0])


class PersonStructuredDataContractTest(unittest.TestCase):
    def test_source_and_generated_person_data_match(self):
        source = load_person("frontend/index.html")
        generated = load_person("html/index.html")
        self.assertEqual(source, generated)
        self.assertEqual(source["@context"], "https://schema.org")
        self.assertEqual(source["@type"], "Person")
        self.assertEqual(source["@id"], "https://rozkalns.net/#person")
        self.assertEqual(source["name"], "Andris Rožkalns")
        self.assertEqual(source["url"], "https://rozkalns.net/")
        self.assertEqual(source["image"], "https://rozkalns.net/photo.jpg")
        self.assertEqual(source["jobTitle"], "Junior DevOps & Linux Engineer")
        self.assertEqual(source["sameAs"], ["https://github.com/rozkalnsandris"])

    def test_location_languages_and_privacy_boundary(self):
        person = load_person("frontend/index.html")
        address = person["homeLocation"]["address"]
        self.assertEqual(address["addressLocality"], "Dortmund")
        self.assertEqual(address["addressCountry"], "DE")
        self.assertEqual(
            [language["alternateName"] for language in person["knowsLanguage"]],
            ["lv", "en", "de"],
        )
        serialized = json.dumps(person, sort_keys=True)
        for forbidden in (
            "telephone",
            "streetAddress",
            "postalCode",
            "birthDate",
            "spouse",
            "children",
            "familyName",
        ):
            self.assertNotIn(f'"{forbidden}"', serialized)


if __name__ == "__main__":
    unittest.main()
