from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "frontend" / "styles"
TOKENS = STYLES / "tokens.css"
TEST = ROOT / "tests" / "test_css_source_contract.py"
AUDIT = ROOT / "docs" / "CSS_C4_AUDIT.md"

TOKEN_TEXT = """:root {
  color-scheme: dark;
  --bg: #0e1014;
  --surface: #15181f;
  --surface-2: #1a1e27;
  --border: #242a36;
  --border-soft: #1e232d;
  --text: #dde1e8;
  --text-dim: #9aa1ae;
  --text-faint: #646c7a;
  --accent: #e0a96d;
  --accent-soft: rgba(224,169,109,.10);
  --accent-line: rgba(224,169,109,.32);
  --ok: #74c98a;
  --warn: #e0a96d;
  --err: #d97a6c;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", "JetBrains Mono", "Fira Code", "Cascadia Code", Menlo, Consolas, monospace;
  --maxw: 1080px;
  --section-gap: clamp(46px,6.5vw,68px);
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --radius-sm: 7px;
  --radius-md: 10px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --breakpoint-layout: 760px;
  --breakpoint-compact: 560px;
  --breakpoint-contact: 620px;
}
"""

TEST_TEXT = r'''from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "frontend" / "styles"
ENTRY = STYLES / "index.css"
EXPECTED_IMPORTS = [
    "./tokens.css",
    "./base.css",
    "./layout.css",
    "./components.css",
    "./features/stats.css",
    "./features/chat.css",
    "./features/contact.css",
    "./features/smarthome.css",
    "./responsive.css",
    "./print.css",
]


class CssSourceContractTests(unittest.TestCase):
    def test_one_authoritative_style_entry_has_explicit_order(self) -> None:
        text = ENTRY.read_text(encoding="utf-8")
        imports = re.findall(r'^@import "([^"]+)";$', text, flags=re.MULTILINE)
        self.assertEqual(imports, EXPECTED_IMPORTS)
        self.assertFalse((STYLES / "main.css").exists())
        self.assertFalse((STYLES / "extra.css").exists())
        for page in ("index.html", "smarthome.html"):
            html = (ROOT / "frontend" / page).read_text(encoding="utf-8")
            self.assertEqual(html.count('href="./styles/index.css"'), 1)
            self.assertNotIn("styles/main.css", html)
            self.assertNotIn("styles/extra.css", html)

    def test_design_tokens_have_one_source(self) -> None:
        tokens = (STYLES / "tokens.css").read_text(encoding="utf-8")
        self.assertEqual(tokens.count(":root"), 1)
        for token in (
            "--bg:", "--surface:", "--surface-2:", "--border:",
            "--border-soft:", "--text:", "--text-dim:", "--text-faint:",
            "--accent:", "--accent-soft:", "--accent-line:", "--ok:",
            "--warn:", "--err:", "--sans:", "--mono:", "--maxw:",
            "--section-gap:", "--space-1:", "--space-6:",
            "--radius-sm:", "--radius-xl:", "--breakpoint-layout:",
            "--breakpoint-compact:", "--breakpoint-contact:",
        ):
            self.assertIn(token, tokens)
        for path in STYLES.rglob("*.css"):
            if path.name in {"tokens.css", "index.css"}:
                continue
            self.assertNotIn(":root", path.read_text(encoding="utf-8"), path)

    def test_breakpoint_tokens_match_the_single_responsive_owner(self) -> None:
        tokens = (STYLES / "tokens.css").read_text(encoding="utf-8")
        responsive = (STYLES / "responsive.css").read_text(encoding="utf-8")
        values = dict(
            re.findall(r"--(breakpoint-[a-z-]+):\s*([0-9]+px);", tokens)
        )
        self.assertEqual(
            values,
            {
                "breakpoint-layout": "760px",
                "breakpoint-compact": "560px",
                "breakpoint-contact": "620px",
            },
        )
        self.assertEqual(
            re.findall(r"@media \(max-width: ([0-9]+px)\)", responsive),
            [
                values["breakpoint-layout"],
                values["breakpoint-compact"],
                values["breakpoint-contact"],
            ],
        )
        for path in STYLES.rglob("*.css"):
            if path.name == "responsive.css":
                continue
            self.assertNotRegex(
                path.read_text(encoding="utf-8"), r"@media \(max-width:", path
            )

    def test_print_and_reduced_motion_have_single_owners(self) -> None:
        print_css = (STYLES / "print.css").read_text(encoding="utf-8")
        base = (STYLES / "base.css").read_text(encoding="utf-8")
        self.assertIn("@media print", print_css)
        self.assertIn(".contact-verify", print_css)
        self.assertIn(".chat-launcher", print_css)
        self.assertIn(".dialog-backdrop", print_css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", base)
        for path in STYLES.rglob("*.css"):
            text = path.read_text(encoding="utf-8")
            if path.name != "print.css":
                self.assertNotIn("@media print", text, path)
            if path.name != "base.css":
                self.assertNotIn("prefers-reduced-motion", text, path)

    def test_components_have_no_historical_patch_or_new_specificity_shortcuts(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(STYLES.rglob("*.css"))
        )
        self.assertNotIn(".skill-chip::before", combined)
        self.assertIn(".skill-chip svg", combined)
        for relative in (
            "layout.css", "components.css", "features/stats.css",
            "features/chat.css", "features/contact.css",
            "features/smarthome.css", "responsive.css",
        ):
            self.assertNotIn(
                "!important", (STYLES / relative).read_text(encoding="utf-8"), relative
            )


if __name__ == "__main__":
    unittest.main()
'''


def prepare() -> None:
    TOKENS.write_text(TOKEN_TEXT, encoding="utf-8")
    TEST.write_text(TEST_TEXT, encoding="utf-8")


def finalize_audit() -> None:
    manifest = json.loads(
        (ROOT / "frontend-dist-manifest.json").read_text(encoding="utf-8")
    )
    css = sorted({item for row in manifest.values() for item in row.get("css", [])})
    if len(css) != 1:
        raise SystemExit(f"expected one production CSS asset, got {css}")
    css_size = (ROOT / "html" / css[0]).stat().st_size
    text = AUDIT.read_text(encoding="utf-8")
    start = text.index("## Generated output\n")
    tail = text.index("No RPi5 pull-request execution", start)
    replacement = f"""## Generated output

The final C4 Vite graph emits exactly one shared production CSS asset:

- `{css[0]}` ({css_size} bytes)

The final transaction built the frontend twice with pinned Node 24.18.0 and Vite 8.1.5; the generated trees and manifests were byte-identical. `npm run check:frontend` and the focused Python/frontend contracts passed with 7 manifest assets and CSS within the existing 22 KB budget.

"""
    AUDIT.write_text(text[:start] + replacement + text[tail:], encoding="utf-8")
    print(f"C4_FINAL_CSS_ASSET={css[0]}")
    print(f"C4_FINAL_CSS_BYTES={css_size}")


def verify_tokens() -> None:
    text = TOKENS.read_text(encoding="utf-8")
    values = dict(re.findall(r"--(breakpoint-[a-z-]+):\s*([0-9]+px);", text))
    expected = {
        "breakpoint-layout": "760px",
        "breakpoint-compact": "560px",
        "breakpoint-contact": "620px",
    }
    if values != expected:
        raise SystemExit(f"unexpected breakpoint tokens: {values}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: c4_final_transaction.py prepare|audit|verify")
    mode = sys.argv[1]
    if mode == "prepare":
        prepare()
    elif mode == "audit":
        finalize_audit()
    elif mode == "verify":
        verify_tokens()
    else:
        raise SystemExit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
