from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {count}: {old[:90]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "frontend/index.html",
    '<img class="profile-photo" src="/photo.jpg" alt="Andris Rožkalns" width="118" height="118">',
    '<img class="profile-photo" src="./photo.webp" alt="Andris Rožkalns" width="118" height="118">',
)

replace_once(
    "nginx.conf",
    'location ~* "^/(?:assets|i18n)/.+\\.[0-9a-f]{12}\\.(?:css|json)$" {',
    'location ~* "^/(?:assets|i18n)/.+\\.[0-9a-f]{12}\\.(?:css|json|webp)$" {',
)

replace_once(
    "scripts/check-frontend-dist.mjs",
    'const HASHED = /\\.[0-9a-f]{12}\\.(?:mjs|js|css|json)$/;',
    'const HASHED = /\\.[0-9a-f]{12}\\.(?:mjs|js|css|json|webp)$/;',
)
replace_once(
    "scripts/check-frontend-dist.mjs",
    'const css = actualAssets.filter((file) => file.endsWith(".css"));\nconst budgets = {',
    'const css = actualAssets.filter((file) => file.endsWith(".css"));\nconst images = actualAssets.filter((file) => file.endsWith(".webp"));\nassert.equal(images.length, 1, "exactly one hashed WebP profile asset is required");\nassert.match(images[0], /^assets\\/photo\\.[0-9a-f]{12}\\.webp$/);\nconst nginxSource = await readFile(resolve(root, "nginx.conf"), "utf8");\nassert.match(nginxSource, /\\(\\?:css\\|json\\|webp\\)\\$\\\"/);\nconst budgets = {',
)
replace_once(
    "scripts/check-frontend-dist.mjs",
    '  css: [await totalBytes(css), 22_000],\n  translations:',
    '  css: [await totalBytes(css), 22_000],\n  images: [await totalBytes(images), 13_000],\n  translations:',
)

replace_once(
    "tests/test_html_semantics.py",
    'HASHED_ASSET = re.compile(r"\\.[0-9a-f]{12}\\.(?:css|mjs|json)$")',
    'HASHED_ASSET = re.compile(r"\\.[0-9a-f]{12}\\.(?:css|mjs|json|webp)$")',
)
replace_once(
    "tests/test_html_semantics.py",
    '        self.assertEqual(len(skip_links), 1)\n\n    def test_fingerprinted_assets_are_manifest_owned',
    '''        self.assertEqual(len(skip_links), 1)\n\n    def test_profile_photo_uses_hashed_webp_with_explicit_dimensions(self) -> None:\n        parsed = parse(HTML_ROOT / "index.html")\n        photos = [\n            row for row in parsed.elements\n            if row.tag == "img" and row.attrs.get("class") == "profile-photo"\n        ]\n        self.assertEqual(len(photos), 1)\n        photo = photos[0]\n        self.assertRegex(\n            photo.attrs.get("src", ""),\n            r"^/assets/photo\\.[0-9a-f]{12}\\.webp$",\n        )\n        self.assertEqual(photo.attrs.get("width"), "118")\n        self.assertEqual(photo.attrs.get("height"), "118")\n        self.assertEqual(photo.attrs.get("alt"), "Andris Rožkalns")\n\n    def test_fingerprinted_assets_are_manifest_owned''',
)

audit = (
    "# Gate C7 — static payload and cache audit\n\n"
    "Baseline: C6 production SHA `81a1cfcb63d53a7b05e1304907c1951495ca2d9b`.\n\n"
    "## Inventory\n\n"
    "- Profile JPEG: 29,454 bytes, 480×480, SHA-256 `f9a54c7dd9df18ed6938981b418d8a5d7b4068efc26962a9a489c4957f93e6aa`.\n"
    "- HTML reserves the rendered profile image at 118×118.\n"
    "- Favicon SVG: 369 bytes; no format optimization is justified.\n"
    "- PDFs are stable download URLs and remain byte-identical: EN 117,269 B / `1234942691c7bd90502f43fabdf312267567cad0e5d0a09f9ab427e024364776`; DE 119,532 B / `3e03d46adc75b95c9359802f5e6b5d541a6a8bbcd663300dbc5f2657b1ff7b64`; LV 117,665 B / `a1677d8160f96516aa73595ca9959ad5d52f63f4363259fd29eb64091a6736b0`.\n\n"
    "## Cache audit\n\n"
    "Pinned Nginx origin run `31264671874` confirmed HTML uses `Cache-Control: no-cache`; stable photo/favicon/PDF URLs use a one-hour freshness lifetime; and content-hashed JS/CSS/i18n assets use one-year `immutable` caching. GitHub-hosted probes against the public Cloudflare edge were excluded because the edge returned a bot challenge; edge/origin policy is deferred to C8.\n\n"
    "## Image candidate\n\n"
    "Read-only run `31264744352` encoded the same 480×480 JPEG with libwebp/cwebp 1.3.2, `-preset photo -m 6`:\n\n"
    "| Candidate | Bytes | Saving vs JPEG | All-PSNR |\n"
    "|---|---:|---:|---:|\n"
    "| WebP q80 | 9,474 | 67.83% | 44.19 dB |\n"
    "| WebP q85 | 12,240 | 58.44% | 45.77 dB |\n"
    "| WebP q90 | 17,576 | 40.33% | 47.96 dB |\n\n"
    "q85 was selected after visual comparison against the committed JPEG: it preserves the 480×480 source dimensions and appearance while removing 17,214 bytes from the normal profile-image transfer. The original JPEG remains at `/photo.jpg` for the Open Graph URL; the rendered CV references `frontend/photo.webp`, which Vite emits as a content-hashed asset.\n\n"
    "## Decision\n\n"
    "- Add only the q85 WebP to the Vite asset graph.\n"
    "- Keep the original JPEG for Open Graph compatibility and as the canonical stable social-image URL.\n"
    "- Extend the existing immutable hashed-asset cache rule to WebP.\n"
    "- Do not change PDFs, favicon, runtime endpoints, Cloudflare ownership, or the deploy model.\n"
    "- Preserve explicit 118×118 image dimensions and all C6 accessibility behavior.\n\n"
    "`PRODUCTION_IMPACT=yes` because the served profile asset and Nginx cache matching change.\n"
)
(ROOT / "docs/C7_STATIC_AUDIT.md").write_text(audit, encoding="utf-8")

print("C7_SOURCE_TRANSFORM=PASS")
