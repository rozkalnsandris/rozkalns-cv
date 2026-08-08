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
            self.assertIn('href="./styles/index.css"', html)
            self.assertNotIn("styles/main.css", html)
            self.assertNotIn("styles/extra.css", html)

    def test_design_tokens_have_one_source(self) -> None:
        tokens = (STYLES / "tokens.css").read_text(encoding="utf-8")
        self.assertEqual(tokens.count(":root"), 1)
        for token in (
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
            self.assertIn(token, tokens)

        for path in STYLES.rglob("*.css"):
            if path.name in {"tokens.css", "index.css"}:
                continue
            self.assertNotIn(":root", path.read_text(encoding="utf-8"), path)

    def test_breakpoint_tokens_match_the_single_responsive_owner(self) -> None:
        tokens = (STYLES / "tokens.css").read_text(encoding="utf-8")
        responsive = (STYLES / "responsive.css").read_text(encoding="utf-8")
        values = dict(
            re.findall(
                r"--(breakpoint-[a-z-]+):\s*([0-9]+px);",
                tokens,
            )
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

    def test_responsive_print_and_reduced_motion_have_single_owners(self) -> None:
        responsive = (STYLES / "responsive.css").read_text(encoding="utf-8")
        print_css = (STYLES / "print.css").read_text(encoding="utf-8")
        base = (STYLES / "base.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 760px)", responsive)
        self.assertIn("@media (max-width: 560px)", responsive)
        self.assertIn("@media (max-width: 620px)", responsive)
        self.assertIn("@media print", print_css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", base)

        for path in STYLES.rglob("*.css"):
            text = path.read_text(encoding="utf-8")
            if path.name != "responsive.css":
                self.assertNotRegex(text, r"@media \(max-width:", path)
            if path.name != "print.css":
                self.assertNotIn("@media print", text, path)
            if path.name != "base.css":
                self.assertNotIn("prefers-reduced-motion", text, path)

    def test_skill_icon_has_no_historical_pseudo_element_patch(self) -> None:
        css = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(STYLES.rglob("*.css"))
        )
        self.assertNotIn(".skill-chip::before", css)
        self.assertIn(".skill-chip svg", css)


if __name__ == "__main__":
    unittest.main()
