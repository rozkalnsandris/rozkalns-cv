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
MANIFEST = ROOT / "frontend-dist-manifest.json"
SOURCE_LAYOUT = ROOT / "frontend" / "styles" / "layout.css"
SOURCE_RESPONSIVE = ROOT / "frontend" / "styles" / "responsive.css"
SOURCE_APP = ROOT / "frontend" / "app.mjs"
SOURCE_CHAT = ROOT / "frontend" / "features" / "chat.mjs"
SOURCE_I18N = ROOT / "frontend" / "core" / "i18n.mjs"
SOURCE_SMART = ROOT / "frontend" / "smarthome.mjs"
TRANSLATIONS = [
    ROOT / "content" / "translations" / "en.json",
    ROOT / "content" / "translations" / "de.json",
    ROOT / "content" / "translations" / "lv.json",
]
HASHED_ASSET = re.compile(r"\.[0-9a-f]{12}\.(?:css|mjs|js|json|webp)$")
NON_EXECUTABLE_DATA_SCRIPT_TYPES = {"application/ld+json"}


def load_manifest() -> dict[str, dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def generated_assets() -> set[str]:
    paths: set[str] = set()
    for row in load_manifest().values():
        file = row.get("file")
        if isinstance(file, str):
            paths.add(file)
        for key in ("css", "assets"):
            for item in row.get(key, []):
                paths.add(item)
    return paths


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts_without_src = 0
        self.inline_handlers: list[str] = []
        self.inline_styles = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if (
            tag == "script"
            and not values.get("src")
            and values.get("type", "").lower() not in NON_EXECUTABLE_DATA_SCRIPT_TYPES
        ):
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

        assets = generated_assets()
        self.assertGreaterEqual(len(assets), 7)
        self.assertGreaterEqual(sum(path.endswith(".css") for path in assets), 1)
        self.assertGreaterEqual(sum(path.endswith((".mjs", ".js")) for path in assets), 3)
        for relative in assets:
            self.assertRegex(relative, HASHED_ASSET)
            self.assertTrue((ROOT / "html" / relative).is_file(), relative)

    def test_compose_recreate_identity_tracks_nginx_config(self) -> None:
        nginx_digest = hashlib.sha256(NGINX.read_bytes()).hexdigest()
        compose = COMPOSE.read_text(encoding="utf-8")
        self.assertIn(
            f'net.rozkalns.cv.nginx-config-sha256: "{nginx_digest}"',
            compose,
        )

    def test_module_cache_key_tracks_nginx_config(self) -> None:
        nginx_digest = hashlib.sha256(NGINX.read_bytes()).hexdigest()
        app_file = load_manifest()["index.html"]["file"]
        self.assertRegex(app_file, r"^assets/app\.[0-9a-f]{12}\.mjs$")
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn(
            f'src="/{app_file}?cfg={nginx_digest[:12]}"',
            text,
        )

    def test_rich_layout_and_sections_are_not_simplified_away(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        layout = SOURCE_LAYOUT.read_text(encoding="utf-8")
        responsive = SOURCE_RESPONSIVE.read_text(encoding="utf-8")
        for section_id in (
            "about", "stats", "experience", "projects", "skills", "education"
        ):
            self.assertIn(f'id="{section_id}"', html)
        self.assertGreaterEqual(html.count('class="project-entry'), 6)
        self.assertGreaterEqual(html.count('class="project-icon"'), 6)
        self.assertGreaterEqual(html.count('class="tech-tag"'), 25)
        self.assertGreaterEqual(html.count('class="skill-chip"'), 20)
        self.assertIn('class="profile-languages"', html)
        self.assertIn('@media (max-width: 760px)', responsive)
        self.assertNotIn('@media (max-width: 850px)', responsive)
        self.assertIn('grid-template-columns: 340px minmax(0,1fr)', layout)

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
        chat = SOURCE_CHAT.read_text(encoding="utf-8")
        for marker in (
            'event.key === "Escape"',
            'event.key !== "Tab"',
            "shell.inert = true",
            "returnFocus?.focus()",
        ):
            self.assertIn(marker, chat)

    def test_shared_i18n_is_used_by_both_entry_points(self) -> None:
        core = SOURCE_I18N.read_text(encoding="utf-8")
        app = SOURCE_APP.read_text(encoding="utf-8")
        smart = SOURCE_SMART.read_text(encoding="utf-8")
        self.assertIn('localStorage', core)
        self.assertIn('"cvlang"', core)
        self.assertIn('./core/i18n.mjs', app)
        self.assertIn('./core/i18n.mjs', smart)
        self.assertNotIn('const TRANSLATIONS', app)
        self.assertNotIn('const TRANSLATIONS', smart)

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
        assets = generated_assets()
        js_bytes = sum(
            (ROOT / "html" / path).stat().st_size
            for path in assets
            if path.endswith((".mjs", ".js"))
        )
        css_bytes = sum(
            (ROOT / "html" / path).stat().st_size
            for path in assets
            if path.endswith(".css")
        )
        limits = {
            INDEX: 21_000,
            SMART: 5_000,
        }
        for path, limit in limits.items():
            self.assertLess(path.stat().st_size, limit, path)
        self.assertLess(js_bytes, 25_000)
        self.assertLess(css_bytes, 22_000)


if __name__ == "__main__":
    unittest.main()
