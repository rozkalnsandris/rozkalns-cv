from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend" / "index.html"
GENERATED = ROOT / "html" / "index.html"
MANIFEST = ROOT / "frontend-dist-manifest.json"
BUILD = ROOT / "scripts" / "build-frontend.mjs"


class SocialPreviewImageTests(unittest.TestCase):
    def test_source_uses_canonical_profile_asset(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            '<meta property="og:image" content="./photo.webp">',
            source,
        )
        self.assertNotIn("photo.jpg", source)

    def test_build_binds_manifest_photo_to_production_origin(self) -> None:
        build = BUILD.read_text(encoding="utf-8")

        self.assertIn('manifest["photo.webp"]?.file', build)
        self.assertIn('^assets\\/photo\\.[0-9a-f]{12}\\.webp$', build)
        self.assertIn('const productionOrigin = "https://rozkalns.net";', build)
        self.assertIn('property="og:image"', build)
        self.assertIn('${productionOrigin}/${photoFile}', build)

    def test_generated_preview_matches_manifest_owned_profile_image(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        photo_file = manifest["photo.webp"]["file"]

        self.assertRegex(photo_file, r"^assets/photo\.[0-9a-f]{12}\.webp$")
        self.assertTrue((ROOT / "html" / photo_file).is_file())

        generated = GENERATED.read_text(encoding="utf-8")
        expected = (
            '<meta property="og:image" '
            f'content="https://rozkalns.net/{photo_file}">'
        )
        self.assertIn(expected, generated)
        self.assertNotRegex(generated, re.compile(r'og:image[^>]+photo\.jpg'))


if __name__ == "__main__":
    unittest.main()
