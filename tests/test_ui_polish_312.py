from pathlib import Path
import re
import unittest

# Issue #312 locks the deliberate recruiter/mobile hierarchy without coupling
# the regression to generated asset fingerprints or browser-only implementation details.
# Browser smoke independently verifies the same hierarchy in real Chromium viewports.
ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
LAYOUT = (ROOT / "frontend" / "styles" / "layout.css").read_text(encoding="utf-8")
COMPONENTS = (ROOT / "frontend" / "styles" / "components.css").read_text(encoding="utf-8")
RESPONSIVE = (ROOT / "frontend" / "styles" / "responsive.css").read_text(encoding="utf-8")
TOKENS = (ROOT / "frontend" / "styles" / "tokens.css").read_text(encoding="utf-8")


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

    def test_primary_projects_are_devops_first_case_studies_with_direct_proof(self) -> None:
        projects = re.findall(r'<article class="project-entry primary">.*?</article>', INDEX, re.S)
        self.assertEqual(len(projects), 4)
        expected = (
            ("p7_title", "rozkalns-cv", "p7_ops"),
            ("p1_title", "RPi5_main", "p1_ops"),
            ("p3_title", "RPi5_main", "p3_ops"),
            ("p2_title", "hermes-tech", "p2_ops"),
        )
        for project, (title_key, repo, ops_key) in zip(projects, expected):
            self.assertIn(f'data-i18n="{title_key}"', project)
            self.assertIn(f'data-i18n="{ops_key}"', project)
            self.assertIn(f"//github.com/rozkalnsandris/{repo}", project)
            self.assertIn('class="tech-tag github-row"', project)

        secondary = re.findall(r'<article class="project-entry secondary">.*?</article>', INDEX, re.S)
        self.assertEqual(len(secondary), 2)
        self.assertIn('data-i18n="p4_title"', secondary[0])
        self.assertIn('href=/smarthome.html', secondary[0])
        self.assertIn('data-i18n=smart_demo', secondary[0])
        self.assertIn('data-i18n="p6_title"', secondary[1])

    def test_compact_nav_is_mobile_first_and_desktop_experience_is_linear(self) -> None:
        self.assertNotIn('@media (max-width:', RESPONSIVE)
        self.assertIn('.site-nav a:first-child, .site-nav a:last-child { display: none; }', COMPONENTS)
        self.assertIn('.site-nav a:first-child, .site-nav a:last-child { display: inline-flex; }', RESPONSIVE)
        self.assertIn('#experience .timeline { grid-template-columns: 1fr; }', RESPONSIVE)
        self.assertNotIn('#experience .timeline { grid-template-columns: repeat(2,minmax(0,1fr));', RESPONSIVE)

    def test_faint_text_meets_aa_on_light_surfaces(self) -> None:
        match = re.search(r'--text-faint:\s*(#[0-9a-fA-F]{6})', TOKENS)
        self.assertIsNotNone(match)
        faint = match.group(1)
        self.assertGreaterEqual(contrast_ratio(faint, "#ffffff"), 4.5)
        self.assertGreaterEqual(contrast_ratio(faint, "#f8f7f4"), 4.5)


if __name__ == "__main__":
    unittest.main()
