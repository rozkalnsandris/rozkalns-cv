from pathlib import Path
import re
import unittest

# Issue #312 locks the deliberate recruiter/mobile hierarchy without coupling
# the regression to generated asset fingerprints or browser-only implementation details.
# Browser smoke independently verifies the same hierarchy in real Chromium viewports.
ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
LAYOUT = (ROOT / "frontend" / "styles" / "v2" / "layout.css").read_text(encoding="utf-8")
COMPONENTS = (ROOT / "frontend" / "styles" / "v2" / "components.css").read_text(encoding="utf-8")
RESPONSIVE = (ROOT / "frontend" / "styles" / "v2" / "responsive.css").read_text(encoding="utf-8")
TOKENS = (ROOT / "frontend" / "styles" / "v2" / "tokens.css").read_text(encoding="utf-8")


def relative_luminance(hex_color: str) -> float:
    value = hex_color.removeprefix("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    high, low = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class RecruiterUiPolishTest(unittest.TestCase):
    def test_hero_promotes_pdf_and_github_without_focus_pill_duplication(self) -> None:
        self.assertNotIn('class="focus-tags"', INDEX)
        self.assertNotIn('"focus focus"', LAYOUT)
        self.assertNotIn('"focus focus photo"', RESPONSIVE)
        actions = re.search(r'<div class="actions">(.*?)</div>', INDEX, re.S)
        self.assertIsNotNone(actions)
        markup = actions.group(1)
        self.assertIn('id="pdfLink"', markup)
        self.assertIn('href=//github.com/rozkalnsandris', markup)
        self.assertNotIn('/smarthome.html', markup)

    def test_six_featured_projects_match_public_sources_and_keep_homelab_proof(self) -> None:
        projects = re.findall(
            r'<article class="project-entry primary project-card"[^>]*>.*?</article>',
            INDEX,
            re.S,
        )
        self.assertEqual(len(projects), 6)
        expectations = (
            ("hermes-tech", "github.com/rozkalnsandris/hermes-tech", "tech.rozkalns.net/"),
            ("hermes-deals", "github.com/rozkalnsandris/hermes-deals", "deals.rozkalns.net/"),
            ("weather", "github.com/rozkalnsandris/rozkalns_weather", None),
            ("coloring-pages", "github.com/rozkalnsandris/coloring-pages", "ausmalwiese.de/"),
            ("cv-platform", "github.com/rozkalnsandris/rozkalns-cv", "rozkalns.net/"),
            ("homelab", "github.com/rozkalnsandris/RPi5_main", "/en/proof/#homelab"),
        )
        for project, (slug, source, destination) in zip(projects, expectations, strict=True):
            self.assertIn(f'data-project-slug="{slug}"', project)
            self.assertIn(source, project)
            if destination:
                self.assertIn(destination, project)
        self.assertIn('data-ui-i18n="v2_cv_learning_body"', projects[4])
        self.assertIn('data-ui-i18n="v2_homelab_learning_body"', projects[5])
        self.assertNotIn("weather.rozkalns.net", projects[2])
        self.assertNotIn("linux-operations-lab", "".join(projects))
        secondary = re.findall(
            r'<article class="project-entry secondary project-evidence-card"[^>]*>.*?</article>',
            INDEX,
            re.S,
        )
        self.assertEqual(len(secondary), 1)
        self.assertIn('data-i18n="p3_title"', secondary[0])
        self.assertIn('//github.com/rozkalnsandris/RPi5_main', secondary[0])

    def test_compact_nav_is_mobile_first_and_desktop_experience_is_linear(self) -> None:
        self.assertNotIn('@media (max-width:', RESPONSIVE)
        self.assertIn('.topbar[data-enhanced] .site-nav { display: none; }', COMPONENTS)
        self.assertIn('.topbar[data-enhanced] .site-nav { display: flex;', RESPONSIVE)
        self.assertIn('grid-template-columns: repeat(2,minmax(0,1fr));', COMPONENTS)
        self.assertIn('.hero-shell .actions .button:first-child { grid-column: 1 / -1; }', COMPONENTS)
        self.assertRegex(
            RESPONSIVE,
            r"#experience\s+\.timeline\s*\{\s*grid-template-columns:\s*1fr;",
        )
        self.assertNotIn('#experience .timeline { grid-template-columns: repeat(2,minmax(0,1fr));', RESPONSIVE)

    def test_faint_text_meets_aa_on_light_surfaces(self) -> None:
        match = re.search(r'--text-faint:\s*(#[0-9a-fA-F]{6})', TOKENS)
        self.assertIsNotNone(match)
        faint = match.group(1)
        self.assertGreaterEqual(contrast_ratio(faint, "#ffffff"), 4.5)
        self.assertGreaterEqual(contrast_ratio(faint, "#f8f7f4"), 4.5)


if __name__ == "__main__":
    unittest.main()
