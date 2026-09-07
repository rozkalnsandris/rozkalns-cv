from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"
sys.path.insert(0, str(BOT))

from evidence import (  # noqa: E402
    ApprovedUrlStreamGuard,
    EvidenceRegistry,
    EvidenceRegistryError,
    URL_POLICY_BLOCK_REPLY,
)


class BotEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = EvidenceRegistry.load()

    def test_skill_selection_is_registry_bound_and_capped(self) -> None:
        selected = self.registry.select(
            "What public proof do you have for Docker Compose?", limit=3
        )
        self.assertEqual(
            [record.evidence_id for record in selected],
            ["cv-compose", "portfolio-readme"],
        )
        self.assertLessEqual(len(selected), 3)
        self.assertTrue(
            all(record.url in self.registry.allowed_output_urls for record in selected)
        )

    def test_project_selection_uses_canonical_title_or_id(self) -> None:
        by_title = self.registry.select("Show Monitoring and observability proof")
        by_id = self.registry.select("Tell me about the homelab")
        self.assertIn("prometheus-stats-client", {row.evidence_id for row in by_title})
        self.assertIn("cv-compose", {row.evidence_id for row in by_id})

    def test_appendix_labels_are_readable_in_supported_languages(self) -> None:
        german = self.registry.render_appendix("Welche Erfahrung hast du mit Nginx?")
        latvian = self.registry.render_appendix("Kādi pierādījumi ir par Prometheus?")
        english = self.registry.render_appendix("What proof do you have for Docker?")
        self.assertIn("Öffentliche Nachweise:", german)
        self.assertIn("Publiskie pierādījumi:", latvian)
        self.assertIn("Public evidence:", english)

    def test_allowed_url_survives_stream_chunking(self) -> None:
        guard = ApprovedUrlStreamGuard(self.registry.allowed_output_urls)
        chunks: list[str] = []
        chunks.extend(guard.feed("See https://github.com/rozkalnsandris/rozkalns-cv/blob/main/"))
        chunks.extend(guard.feed("docker-compose.yml now."))
        chunks.extend(guard.finish())
        self.assertFalse(guard.blocked)
        self.assertEqual(
            "".join(chunks),
            "See https://github.com/rozkalnsandris/rozkalns-cv/blob/main/docker-compose.yml now.",
        )

    def test_non_registry_url_is_rejected_across_chunks(self) -> None:
        guard = ApprovedUrlStreamGuard(self.registry.allowed_output_urls)
        chunks: list[str] = []
        chunks.extend(guard.feed("See https://github.com/rozkalnsandris/"))
        chunks.extend(guard.feed("not-approved"))
        self.assertTrue(guard.blocked)
        self.assertIn(URL_POLICY_BLOCK_REPLY, "".join(chunks))
        self.assertNotIn("not-approved", "".join(chunks))

    def test_unknown_evidence_reference_fails_closed(self) -> None:
        payload = json.loads((BOT / "evidence_registry.json").read_text(encoding="utf-8"))
        payload["skill_evidence"]["Docker"] = ["missing-evidence"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(EvidenceRegistryError):
                EvidenceRegistry.load(path)


if __name__ == "__main__":
    unittest.main()
