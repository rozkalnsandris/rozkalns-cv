import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HeroRecruiterScanTests(unittest.TestCase):
    def test_hero_exposes_proven_recruiter_scan_evidence(self) -> None:
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")

        for capability in (
            "Linux",
            "Docker / Compose",
            "Bash",
            "Nginx",
            "Prometheus / Grafana",
        ):
            self.assertIn(capability, html)

        self.assertIn('data-i18n="availability"', html)
        self.assertIn("data-live-state-dot", html)
        self.assertIn("data-live-state-label", html)
        self.assertIn('data-stat="uptime_30d"', html)
        self.assertIn('data-stat="docker_containers"', html)

    def test_operations_first_tagline_and_hero_labels_are_localized(self) -> None:
        expected = {
            "en": "I build and automate self-hosted Linux systems with containers, monitoring and reliable operations. This site runs on infrastructure I operate.",
            "de": "Ich baue und automatisiere selbst gehostete Linux-Systeme mit Containern, Monitoring und zuverlässigem Betrieb. Diese Website läuft auf Infrastruktur, die ich selbst betreibe.",
            "lv": "Es būvēju un automatizēju pašhostētas Linux sistēmas ar konteineriem, monitoringu un uzticamu darbību. Šī vietne darbojas uz infrastruktūras, ko pats uzturu.",
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
        layout = (ROOT / "frontend/styles/layout.css").read_text(encoding="utf-8")
        responsive = (ROOT / "frontend/styles/responsive.css").read_text(
            encoding="utf-8"
        )
        components = (ROOT / "frontend/styles/components.css").read_text(
            encoding="utf-8"
        )

        self.assertIn('"capabilities capabilities"', layout)
        self.assertIn('"meta meta"', layout)
        self.assertIn('"live live"', layout)

        self.assertIn('"capabilities capabilities capabilities photo"', responsive)
        self.assertIn('"meta meta meta photo"', responsive)
        self.assertIn('"live live live photo"', responsive)

        self.assertIn(".capability-strip { grid-area: capabilities;", components)
        self.assertIn(".hero-meta { grid-area: meta;", components)
        self.assertIn(".hero-live-proof { grid-area: live;", components)


if __name__ == "__main__":
    unittest.main()
