import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HeroRecruiterScanTests(unittest.TestCase):
    def test_hero_exposes_proven_recruiter_scan_evidence(self) -> None:
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")

        for capability in (
            "Software testing",
            "Browser regression",
            "Linux",
            "Git / CI",
            "Data validation",
        ):
            self.assertIn(capability, html)

        self.assertIn('data-i18n="availability"', html)
        self.assertIn("data-live-state-dot", html)
        self.assertIn("data-live-state-label", html)
        self.assertIn('data-stat="uptime_30d"', html)
        self.assertIn('data-stat="docker_containers"', html)

    def test_operations_first_tagline_and_hero_labels_are_localized(self) -> None:
        expected = {
            "en": "I test web systems systematically, validate contracts and data, and document failures clearly. My public projects show browser regression testing, Git/CI, Linux, Docker, Python and REST API work.",
            "de": "Ich teste Websysteme systematisch, validiere Contracts und Daten und dokumentiere Fehler klar. Meine öffentlichen Projekte zeigen Browser-Regressionstests, Git/CI, Linux, Docker, Python und REST-API-Arbeit.",
            "lv": "Tīmekļa sistēmas testēju sistemātiski, validēju līgumus un datus un skaidri dokumentēju kļūmes. Mani publiskie projekti rāda pārlūka regresijas testēšanu, Git/CI, Linux, Docker, Python un REST API darbu.",
        }

        required = {
            "hero_capabilities_label",
            "hero_meta_label",
            "hero_location",
            "availability",
            "hero_live_label",
        }

        for language, tagline in expected.items():
            messages = json.loads(
                (ROOT / f"content/translations/{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(messages["tagline"], tagline)
            self.assertTrue(required <= messages.keys())

    def test_hero_live_proof_reuses_existing_stats_controller(self) -> None:
        stats = (ROOT / "frontend/features/stats.mjs").read_text(encoding="utf-8")

        self.assertIn('querySelectorAll?.("[data-live-state-dot]")', stats)
        self.assertIn('querySelectorAll?.("[data-live-state-label]")', stats)
        self.assertIn('fetchImpl(`/stats.json?_=${Date.now()}`', stats)

    def test_recruiter_scan_has_mobile_and_desktop_grid_areas(self) -> None:
        layout = (ROOT / "frontend/styles/v2/layout.css").read_text(encoding="utf-8")
        responsive = (ROOT / "frontend/styles/v2/responsive.css").read_text(
            encoding="utf-8"
        )
        components = (ROOT / "frontend/styles/v2/components.css").read_text(
            encoding="utf-8"
        )

        self.assertIn('"capabilities capabilities"', layout)
        self.assertIn('"meta meta"', layout)
        self.assertIn('#contact', layout)

        self.assertIn('"tagline capabilities photo"', responsive)
        self.assertIn('"meta capabilities photo"', responsive)
        self.assertIn('"actions actions photo"', responsive)

        self.assertIn(".capability-strip { grid-area: capabilities;", components)
        self.assertIn(".hero-meta { grid-area: meta;", components)
        self.assertIn(".hero-live-proof { grid-area: live;", components)


if __name__ == "__main__":
    unittest.main()
