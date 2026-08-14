from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectTechIconTests(unittest.TestCase):
    def test_project_tags_use_shared_progressive_icon_enhancement(self) -> None:
        icons = (ROOT / "frontend/ui/icons.mjs").read_text(encoding="utf-8")
        styles = (ROOT / "frontend/styles/components.css").read_text(encoding="utf-8")

        self.assertIn('root.querySelectorAll(".tech-tag")', icons)
        self.assertIn('element.querySelector("svg")', icons)
        self.assertIn('element.classList?.add?.("has-tech-icon")', icons)
        self.assertIn('enhanceIconPill(tag, root, { hideFallback: true })', icons)

        self.assertIn(".tech-tag.has-tech-icon::before", styles)
        self.assertIn("display: none", styles)
        self.assertIn(".tech-tag svg", styles)
        self.assertIn("width: 12px", styles)
        self.assertIn("height: 12px", styles)

    def test_visible_project_technologies_have_meaningful_icon_families(self) -> None:
        icons = (ROOT / "frontend/ui/icons.mjs").read_text(encoding="utf-8")
        source = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        projects = source.split('<section id="projects">', 1)[1].split(
            '<section id="skills">', 1
        )[0]
        labels = re.findall(r'<span class="tech-tag">([^<]+)</span>', projects)

        self.assertGreaterEqual(len(labels), 20)
        for label in (
            "Raspberry Pi 5",
            "Docker",
            "AdGuard",
            "Cloudflare",
            "Python",
            "LLM routing",
            "ChromaDB",
            "Telegram",
            "Home Assistant",
            "Prometheus",
            "Node Exporter",
            "Matter",
            "MQTT",
            "Energy",
            "APT",
            "Health checks",
            "15 sensors",
            "Relay pump",
            "Multiplexer",
            "Safety limits",
        ):
            self.assertIn(label, labels)

        expected_rules = {
            "database": "chromadb|database|sqlite|postgres|mysql",
            "send": "telegram",
            "shield": "adguard|safety|health check|ssl|tls|ssh|ftp",
            "chart": "prometheus|grafana|node exporter|live metrics|energy",
            "gear": "systemd|apt",
            "chip": "raspberry pi|esp32|iot|matter|sensor|relay|multiplexer",
            "cloud": "ansible|terraform|aws|cloudflare|cloud",
            "network": "dns|network|rest api|nginx|llm routing|mqtt",
        }
        for family, pattern in expected_rules.items():
            self.assertIn(pattern, icons, family)

    def test_tech_icon_svg_is_decorative_and_shared_enhancer_stays_idempotent(self) -> None:
        icons = (ROOT / "frontend/ui/icons.mjs").read_text(encoding="utf-8")

        self.assertIn('svg.setAttribute("aria-hidden", "true")', icons)
        self.assertRegex(
            icons,
            r'if \(!element\.querySelector\("svg"\)\) \{\s*'
            r'element\.prepend\(createIcon\(skillIconName\(element\.textContent\), root\)\);',
        )


if __name__ == "__main__":
    unittest.main()
