from __future__ import annotations

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
            "--warn:", "--err:", "--sans:", "--serif:", "--mono:", "--maxw:",
            "--section-gap:", "--space-1:", "--space-6:",
            "--radius-sm:", "--radius-xl:", "--breakpoint-layout:",
            "--breakpoint-compact:", "--breakpoint-contact:",
        ):
            self.assertIn(token, tokens)
        self.assertIn("color-scheme: light", tokens)
        for path in STYLES.rglob("*.css"):
            if path.name in {"tokens.css", "index.css"}:
                continue
            self.assertNotIn(":root", path.read_text(encoding="utf-8"), path)

    def test_breakpoint_tokens_match_the_mobile_first_responsive_owner(self) -> None:
        tokens = (STYLES / "tokens.css").read_text(encoding="utf-8")
        responsive = (STYLES / "responsive.css").read_text(encoding="utf-8")
        values = dict(re.findall(r"--(breakpoint-[a-z-]+):\s*([0-9]+px);", tokens))
        self.assertEqual(
            values,
            {
                "breakpoint-layout": "900px",
                "breakpoint-compact": "640px",
                "breakpoint-contact": "720px",
            },
        )
        self.assertEqual(
            re.findall(r"@media \(min-width: ([0-9]+px)\)", responsive),
            [values["breakpoint-compact"], values["breakpoint-contact"], values["breakpoint-layout"]],
        )
        self.assertNotIn("@media (max-width:", responsive)
        for path in STYLES.rglob("*.css"):
            if path.name == "responsive.css":
                continue
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"@media \((?:min|max)-width:", path)

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
        combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(STYLES.rglob("*.css")))
        self.assertNotIn(".skill-chip::before", combined)
        self.assertIn(".skill-chip svg", combined)
        for relative in (
            "layout.css", "components.css", "features/stats.css",
            "features/chat.css", "features/contact.css", "features/smarthome.css", "responsive.css",
        ):
            self.assertNotIn("!important", (STYLES / relative).read_text(encoding="utf-8"), relative)


if __name__ == "__main__":
    unittest.main()
