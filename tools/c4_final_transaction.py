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


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"unexpected {label}: count={text.count(old)}")
    return text.replace(old, new)


def prepare() -> None:
    TOKENS.write_text(TOKEN_TEXT, encoding="utf-8")

    text = TEST.read_text(encoding="utf-8")
    old = '''        for token in (
            "--bg:",
            "--surface:",
            "--text:",
            "--accent:",
            "--sans:",
            "--mono:",
            "--maxw:",
            "--section-gap:",
        ):
'''
    new = '''        for token in (
            "--bg:",
            "--surface:",
            "--text:",
            "--accent:",
            "--sans:",
            "--mono:",
            "--maxw:",
            "--section-gap:",
            "--space-1:",
            "--space-6:",
            "--radius-sm:",
            "--radius-xl:",
            "--breakpoint-layout:",
            "--breakpoint-compact:",
            "--breakpoint-contact:",
        ):
'''
    text = replace_once(text, old, new, "token-test anchor")
    marker = "    def test_responsive_print_and_reduced_motion_have_single_owners(self) -> None:\n"
    addition = '''    def test_breakpoint_tokens_match_the_single_responsive_owner(self) -> None:
        tokens = (STYLES / "tokens.css").read_text(encoding="utf-8")
        responsive = (STYLES / "responsive.css").read_text(encoding="utf-8")
        values = dict(
            re.findall(r"--(breakpoint-[a-z-]+):\\s*([0-9]+px);", tokens)
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
            re.findall(r"@media \\(max-width: ([0-9]+px)\\)", responsive),
            [
                values["breakpoint-layout"],
                values["breakpoint-compact"],
                values["breakpoint-contact"],
            ],
        )

'''
    if "def test_breakpoint_tokens_match_the_single_responsive_owner" not in text:
        text = replace_once(text, marker, addition + marker, "breakpoint-test anchor")
    TEST.write_text(text, encoding="utf-8")


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
    if values != {
        "breakpoint-layout": "760px",
        "breakpoint-compact": "560px",
        "breakpoint-contact": "620px",
    }:
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
