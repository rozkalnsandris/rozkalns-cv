from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "html" / "index.html"
SMART = ROOT / "html" / "smarthome.html"
FAVICON = ROOT / "html" / "favicon.svg"
NGINX = ROOT / "nginx.conf"
COMPOSE = ROOT / "docker-compose.yml"
CSS = ROOT / "html" / "assets" / "main.8548550e57d3.css"
APP = ROOT / "html" / "assets" / "app.d878d409f278.mjs"
SMART_JS = ROOT / "html" / "assets" / "smarthome.70da56476fdb.mjs"
TRANSLATIONS = [
    ROOT / "html" / "i18n" / "en.f5b04cdd45df.json",
    ROOT / "html" / "i18n" / "de.3313b3cef4b0.json",
    ROOT / "html" / "i18n" / "lv.788ab6598ca4.json",
]


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts_without_src = 0
        self.inline_handlers: list[str] = []
        self.inline_styles = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and not values.get("src"):
            self.scripts_without_src += 1
        for name, _ in attrs:
            if name.startswith("on"):
                self.inline_handlers.append(name)
            if name == "style":
                self.inline_styles += 1


class FrontendContractTests(unittest.TestCase):
    def test_html_has_no_inline_code_or_styles(self) -> None:
        for path in (INDEX, SMART):
            parser = Parser()
            text = path.read_text(encoding="utf-8")
            parser.feed(text)
            self.assertEqual(parser.scripts_without_src, 0, path)
            self.assertEqual(parser.inline_handlers, [], path)
            self.assertEqual(parser.inline_styles, 0, path)
            self.assertNotIn("<style", text.lower())

    def test_strict_csp_and_immutable_hashed_assets(self) -> None:
        nginx = NGINX.read_text(encoding="utf-8")
        self.assertNotIn("unsafe-inline", nginx)
        self.assertNotIn("unsafe-eval", nginx)
        self.assertIn("frame-ancestors 'none'", nginx)
        self.assertIn("add_header_inherit merge;", nginx)
        self.assertIn("'nonce-$request_id'", nginx)
        self.assertIn("script-src-attr 'none'", nginx)
        self.assertIn(
            "https://static.cloudflareinsights.com/beacon.min.js",
            nginx,
        )
        self.assertIn("connect-src 'self';", nginx)
        self.assertNotIn("cloudflareinsights.com;", nginx)
        self.assertIn(
            'Cache-Control "public, max-age=31536000, immutable"', nginx
        )
        self.assertIn("text/javascript mjs;", nginx)
        self.assertIn("default_type text/javascript;", nginx)
        self.assertIn("text/javascript application/javascript", nginx)
        self.assertNotIn("(?:css|mjs|json)", nginx)
        for path in (CSS, APP, SMART_JS, *TRANSLATIONS):
            self.assertRegex(path.name, r"\.[0-9a-f]{12}\.")
            self.assertTrue(path.is_file(), path)
            embedded = path.name.split(".")[-2]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
            self.assertEqual(embedded, actual, path)

    def test_compose_recreate_identity_tracks_nginx_config(self) -> None:
        nginx_digest = hashlib.sha256(NGINX.read_bytes()).hexdigest()
        compose = COMPOSE.read_text(encoding="utf-8")
        self.assertIn(
            f'net.rozkalns.cv.nginx-config-sha256: "{nginx_digest}"',
            compose,
        )

    def test_module_cache_key_tracks_nginx_config(self) -> None:
        nginx_digest = hashlib.sha256(NGINX.read_bytes()).hexdigest()
        text = INDEX.read_text(encoding="utf-8")
        match = re.search(
            r'src="/assets/app\.[0-9a-f]{12}\.mjs\?cfg=([0-9a-f]{12})"',
            text,
        )
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), nginx_digest[:12])

    def test_rich_layout_and_sections_are_not_simplified_away(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        for section_id in (
            "about", "stats", "experience", "projects", "skills", "education"
        ):
            self.assertIn(f'id="{section_id}"', html)
        self.assertGreaterEqual(html.count('class="project-entry'), 6)
        self.assertGreaterEqual(html.count('class="project-icon"'), 6)
        self.assertGreaterEqual(html.count('class="tech-tag"'), 25)
        self.assertGreaterEqual(html.count('class="skill-chip"'), 20)
        self.assertIn('class="profile-languages"', html)
        self.assertIn('@media (max-width: 760px)', css)
        self.assertNotIn('@media (max-width: 850px)', css)
        self.assertIn('grid-template-columns: 340px minmax(0,1fr)', css)

    def test_cloudflare_analytics_is_not_manually_embedded(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        self.assertNotIn("data-cf-beacon", text)
        self.assertNotIn("static.cloudflareinsights.com/beacon.min.js", text)

    def test_favicon_is_declared_and_present(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        self.assertTrue(FAVICON.is_file())
        self.assertIn(
            '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
            text,
        )

    def test_accessible_dialog_contract(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        for marker in (
            'role="dialog"',
            'aria-modal="true"',
            'aria-labelledby="chatTitle"',
            'aria-describedby="chatPrivacy"',
            'role="log"',
            'aria-live="polite"',
            'aria-busy="false"',
            'aria-pressed="true"',
        ):
            self.assertIn(marker, text)
        app = APP.read_text(encoding="utf-8")
        for marker in (
            'event.key === "Escape"',
            'event.key !== "Tab"',
            "shell.inert = true",
            "returnFocus?.focus()",
        ):
            self.assertIn(marker, app)

    def test_privacy_notice_is_complete_in_every_language(self) -> None:
        for path in TRANSLATIONS:
            data = json.loads(path.read_text(encoding="utf-8"))
            notice = data["chat_privacy"].lower()
            self.assertIn("7", notice)
            self.assertIn("llm", notice)
            self.assertIn("ip", notice)

    def test_translation_keys_match(self) -> None:
        documents = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in TRANSLATIONS
        ]
        self.assertEqual(set(documents[0]), set(documents[1]))
        self.assertEqual(set(documents[0]), set(documents[2]))

    def test_frontend_size_budget(self) -> None:
        limits = {
            INDEX: 20_000,
            CSS: 25_000,
            APP: 20_000,
            SMART: 8_000,
            SMART_JS: 8_000,
        }
        for path, limit in limits.items():
            self.assertLess(path.stat().st_size, limit, path)


if __name__ == "__main__":
    unittest.main()
