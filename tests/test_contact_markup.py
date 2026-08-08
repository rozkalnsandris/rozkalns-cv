from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContactMarkupTests(unittest.TestCase):
    def test_initial_html_does_not_embed_contact_channels(self) -> None:
        index = (ROOT / "html" / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(index, r'(?i)href=["\'](?:mailto|tel):')
        self.assertNotRegex(
            index,
            r"(?i)[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
        )
        self.assertIn('id="contactEmail"', index)
        self.assertIn('id="contactPhone"', index)
        self.assertIn('id="contactReveal"', index)
        self.assertIn('id="turnstileMount"', index)

    def test_contact_config_has_no_embedded_contact_fallbacks(self) -> None:
        source = (ROOT / "bot" / "contact.py").read_text(encoding="utf-8")
        for variable in (
            "CONTACT_EMAIL",
            "CONTACT_PHONE_DISPLAY",
            "CONTACT_PHONE_URI",
        ):
            with self.subTest(variable=variable):
                self.assertIn(f'os.getenv("{variable}", "")', source)
                self.assertNotRegex(
                    source,
                    rf'os\.getenv\("{variable}",\s*"[^\"]+"\)',
                )

    def test_enhancement_sources_are_in_authoritative_build_graph(self) -> None:
        source = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertIn('src="./enhancements.mjs"', source)
        self.assertIn('href="./styles/extra.css"', source)

        manifest = json.loads(
            (ROOT / "frontend-dist-manifest.json").read_text(encoding="utf-8")
        )
        entry = manifest["index.html"]
        self.assertRegex(entry["file"], r"^assets/app\.[0-9a-f]{12}\.mjs$")
        self.assertGreaterEqual(len(entry.get("css", [])), 1)
        for relative in [entry["file"], *entry.get("css", [])]:
            self.assertRegex(relative, r"\.[0-9a-f]{12}\.(?:mjs|css)$")
            self.assertTrue((ROOT / "html" / relative).is_file(), relative)

    def test_turnstile_csp_is_minimal_and_strict(self) -> None:
        nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn(
            "script-src 'self' 'nonce-$request_id' "
            "https://static.cloudflareinsights.com/beacon.min.js "
            "https://challenges.cloudflare.com;",
            nginx,
        )
        self.assertIn("frame-src https://challenges.cloudflare.com;", nginx)
        self.assertIn("connect-src 'self';", nginx)
        self.assertNotIn("unsafe-inline", nginx)
        self.assertNotIn("unsafe-eval", nginx)

    def test_skill_diamond_marker_is_disabled_by_icon_layer(self) -> None:
        css = (ROOT / "frontend" / "styles" / "extra.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(".skill-chip::before { content: none; }", css)
        self.assertIn(".skill-chip svg", css)


if __name__ == "__main__":
    unittest.main()
