from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend" / "index.html"
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


if __name__ == "__main__":
    unittest.main()
