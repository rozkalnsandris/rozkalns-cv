import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RecruiterCopy417Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.messages = {
            language: json.loads(
                (ROOT / "content" / "translations" / f"{language}.json").read_text(encoding="utf-8")
            )
            for language in ("en", "de", "lv")
        }

    def test_translation_key_parity(self) -> None:
        keys = [set(messages) for messages in self.messages.values()]
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(keys[0], keys[2])

    def test_recruiter_copy_regressions(self) -> None:
        en, de, lv = (self.messages[language] for language in ("en", "de", "lv"))

        self.assertEqual(en["e1_dates"], "Jul 2023 – Dec 2026 (planned)")
        self.assertIn("Processed high-volume", en["e1_b1"])
        self.assertNotIn("before/after evidence", en["p3_ops"])

        self.assertEqual(de["skills_working"], "Praktische Kenntnisse")
        self.assertEqual(de["e1_dates"], "Juli 2023 – Dez. 2026 (geplant)")
        self.assertEqual(de["e2_dates"], "Mai 2020 – Juni 2023")
        self.assertNotIn("Vorher-/Nachher-Evidenz", de["p3_ops"])
        self.assertNotIn("Praxiserfahrung", de["skills_working"])

        self.assertEqual(lv["e1_dates"], "2023. g. jūlijs – plānots līdz 2026. g. decembrim")
        self.assertNotIn("jũlijs", lv["e1_dates"])
        self.assertNotIn("pirms/pēc pierādījumi", lv["p3_ops"])

    def test_learning_skills_remain_learning_only(self) -> None:
        for messages in self.messages.values():
            learning = messages["skills_learning_items"]
            self.assertIn("Terraform", learning)
            self.assertIn("AWS Cloud", learning)
            self.assertNotIn("Terraform", messages["skills_core_items"])
            self.assertNotIn("AWS Cloud", messages["skills_core_items"])

    def test_major_skills_connect_to_project_proof(self) -> None:
        source = (ROOT / "frontend" / "ui" / "icons.mjs").read_text(encoding="utf-8")
        for proof in (
            '"rozkalns-cv": "Linux · Docker Compose · Nginx"',
            '"RPi5_main": "Prometheus · Bash"',
            '"hermes-tech": "Python"',
            '"home-assistant-config": "Home Assistant · YAML"',
            "skill-proof-text",
        ):
            self.assertIn(proof, source)


if __name__ == "__main__":
    unittest.main()
