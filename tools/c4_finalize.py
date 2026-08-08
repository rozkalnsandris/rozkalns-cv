from __future__ import annotations

from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "frontend" / "styles"
OLD_MAIN = STYLE / "main.css"
OLD_EXTRA = STYLE / "extra.css"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"unexpected {label}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    main_bytes = OLD_MAIN.read_bytes()
    extra_bytes = OLD_EXTRA.read_bytes()

    replace_once(
        ROOT / "frontend" / "index.html",
        '  <link rel="stylesheet" href="./styles/main.css">\n  <link rel="stylesheet" href="./styles/extra.css">',
        '  <link rel="stylesheet" href="./styles/index.css">',
        "CV stylesheet source contract",
    )
    replace_once(
        ROOT / "frontend" / "smarthome.html",
        '  <link rel="stylesheet" href="./styles/main.css">',
        '  <link rel="stylesheet" href="./styles/index.css">',
        "Smart Home stylesheet source contract",
    )

    replace_once(
        ROOT / "scripts" / "validate-source.sh",
        "    frontend/styles/main.css \\\n    frontend/styles/extra.css \\\n",
        "    frontend/styles/index.css \\\n    frontend/styles/tokens.css \\\n    frontend/styles/base.css \\\n    frontend/styles/layout.css \\\n    frontend/styles/components.css \\\n    frontend/styles/features/stats.css \\\n    frontend/styles/features/chat.css \\\n    frontend/styles/features/contact.css \\\n    frontend/styles/features/smarthome.css \\\n    frontend/styles/responsive.css \\\n    frontend/styles/print.css \\\n",
        "validator stylesheet block",
    )
    replace_once(
        ROOT / "scripts" / "validate-source.sh",
        "for retired in update.sh update_cv-1.sh cloudflared.env.example; do",
        "for retired in update.sh update_cv-1.sh cloudflared.env.example frontend/styles/main.css frontend/styles/extra.css; do",
        "validator retired loop",
    )

    contract = ROOT / "tests" / "test_frontend_contract.py"
    replace_once(
        contract,
        'SOURCE_CSS = ROOT / "frontend" / "styles" / "main.css"',
        '''STYLE_ROOT = ROOT / "frontend" / "styles"\nSOURCE_CSS_FILES = (\n    STYLE_ROOT / "tokens.css",\n    STYLE_ROOT / "base.css",\n    STYLE_ROOT / "layout.css",\n    STYLE_ROOT / "components.css",\n    STYLE_ROOT / "features" / "stats.css",\n    STYLE_ROOT / "features" / "chat.css",\n    STYLE_ROOT / "features" / "contact.css",\n    STYLE_ROOT / "features" / "smarthome.css",\n    STYLE_ROOT / "responsive.css",\n    STYLE_ROOT / "print.css",\n)''',
        "frontend contract CSS source constant",
    )
    replace_once(
        contract,
        '        css = SOURCE_CSS.read_text(encoding="utf-8")',
        '        css = "\\n".join(path.read_text(encoding="utf-8") for path in SOURCE_CSS_FILES)',
        "frontend contract CSS read",
    )
    replace_once(
        contract,
        "        self.assertGreaterEqual(len(assets), 8)",
        '        self.assertGreaterEqual(len(assets), 7)\n        css_assets = [path for path in assets if path.endswith(".css")]\n        self.assertEqual(len(css_assets), 1, css_assets)',
        "frontend asset-count contract",
    )

    tokens = STYLE / "tokens.css"
    token_text = tokens.read_text(encoding="utf-8")
    needle = "  --section-gap: clamp(46px,6.5vw,68px);\n"
    additions = (
        "  --space-1: 4px;\n"
        "  --space-2: 8px;\n"
        "  --space-3: 12px;\n"
        "  --space-4: 16px;\n"
        "  --space-5: 20px;\n"
        "  --space-6: 24px;\n"
        "  --radius-sm: 7px;\n"
        "  --radius-md: 10px;\n"
        "  --radius-lg: 12px;\n"
        "  --radius-xl: 16px;\n"
    )
    if additions not in token_text:
        if token_text.count(needle) != 1:
            raise SystemExit("unexpected token insertion point")
        tokens.write_text(token_text.replace(needle, needle + additions), encoding="utf-8")

    audit = ROOT / "docs" / "CSS_C4_AUDIT.md"
    audit.write_text(
        f"""# Gate C4 CSS source audit

## Frozen C3 baseline

- `frontend/styles/main.css`: {len(main_bytes.splitlines())} lines, SHA-256 `{sha256(main_bytes).hexdigest()}`.
- `frontend/styles/extra.css`: {len(extra_bytes.splitlines())} lines, SHA-256 `{sha256(extra_bytes).hexdigest()}`.
- CV source loaded `main.css` followed by `extra.css`; Smart Home loaded only `main.css`.

## Selector overlap

The only intentional historical override between the two source files is `.skill-chip::before`: `main.css` supplied the legacy diamond marker and `extra.css` suppressed it after SVG skill icons were introduced. C4 removes the pseudo-element rule entirely and keeps `.skill-chip svg` as the authoritative component behavior.

The remaining `extra.css` rules are contact-verification/action-icon feature rules plus its mobile/print conditions. They move to responsibility-owned modules instead of remaining a later patch layer.

## C4 ownership

- `tokens.css`: visual tokens.
- `base.css`: reset, document defaults, focus, reduced motion.
- `layout.css`: page/sidebar/section layout.
- `components.css`: shared UI and CV content components.
- `features/stats.css`: live statistics.
- `features/chat.css`: assistant dialog.
- `features/contact.css`: Turnstile/contact reveal.
- `features/smarthome.css`: Smart Home demo.
- `responsive.css`: all max-width breakpoints (760px, 560px, 620px).
- `print.css`: all print-only behavior.
- `index.css`: the single ordered source entry consumed by both HTML entry points.
""",
        encoding="utf-8",
    )

    OLD_MAIN.unlink()
    OLD_EXTRA.unlink()


if __name__ == "__main__":
    main()
