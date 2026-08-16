from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
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
        actions = re.search(r'<div class="actions">(.*?)</div>', INDEX, re.S)
        self.assertIsNotNone(actions)
        markup = actions.group(1)
        self.assertIn('id="pdfLink"', markup)
        self.assertIn('href=//github.com/rozkalnsandris', markup)
        self.assertNotIn('/smarthome.html', markup)

    def test_primary_projects_have_direct_proof_and_home_demo(self) -> None:
        projects = re.findall(r'<article class="project-entry primary">.*?</article>', INDEX, re.S)
        self.assertEqual(len(projects), 3)
        expected = ("hermes-tech", "RPi5_main", "home-assistant-config")
        for project, repo in zip(projects, expected):
            self.assertIn(f"//github.com/rozkalnsandris/{repo}", project)
            self.assertIn('class="tech-tag github-row"', project)
        self.assertIn('href=/smarthome.html', projects[2])
        self.assertIn('data-i18n=smart_demo', projects[2])

    def test_compact_nav_and_desktop_experience_are_linear(self) -> None:
        self.assertIn('@media (max-width: 639px)', RESPONSIVE)
        self.assertIn('.site-nav a:first-child, .site-nav a:last-child { display: none; }', RESPONSIVE)
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
