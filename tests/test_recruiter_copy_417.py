import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "content" / "translations"
RUNTIME_I18N = ROOT / "frontend" / "core" / "i18n.mjs"
LOCALIZER = ROOT / "scripts" / "localize-frontend.mjs"

WEB_OVERRIDE_KEYS = {
    "web_e1_dates",
    "web_e1_b1",
    "web_e1_b2",
    "web_e2_dates",
    "web_e2_title",
    "web_e2_b1",
    "web_e3_title",
    "web_skills_working",
}


class RecruiterCopy417Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.messages = {
            language: json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
            for language in ("en", "de", "lv")
        }

    def test_translation_keys_remain_aligned_and_web_overrides_are_explicit(self) -> None:
        key_sets = [set(messages) for messages in self.messages.values()]
        self.assertEqual(key_sets[0], key_sets[1])
        self.assertEqual(key_sets[1], key_sets[2])
        for messages in self.messages.values():
            self.assertTrue(WEB_OVERRIDE_KEYS.issubset(messages))

    def test_runtime_and_static_localizer_resolve_web_overrides(self) -> None:
        for path in (RUNTIME_I18N, LOCALIZER):
            source = path.read_text(encoding="utf-8")
            self.assertIn("function webMessage(messages, key)", source)
            self.assertIn("messages[`web_${key}`]", source)
            self.assertIn("webMessage(messages", source)

    def test_german_web_copy_is_recruiter_friendly_without_changing_pdf_base(self) -> None:
        de = self.messages["de"]
        self.assertEqual(de["web_skills_working"], "Praktische Kenntnisse")
        self.assertEqual(de["web_e1_dates"], "Juli 2023 – Dez. 2026 (geplant)")
        self.assertIn("Bestellungen im Elektro-Großhandel", de["web_e1_b1"])
        self.assertIn("Zustandsprüfungen vor und nach dem Update", de["p3_ops"])
        self.assertNotIn("Vorher-/Nachher-Evidenz", de["p3_ops"])

        # PDF-relevant base strings stay pinned to the accepted PDF projection.
        self.assertEqual(de["skills_working"], "Praxiserfahrung")
        self.assertEqual(de["e1_dates"], "Jul 2023 – Dez 2026 geplant")

    def test_english_web_copy_is_direct_and_scan_friendly(self) -> None:
        en = self.messages["en"]
        self.assertEqual(en["web_e1_dates"], "Jul 2023 – Dec 2026 (planned)")
        self.assertIn("Processed high-volume electrical wholesale orders", en["web_e1_b1"])
        self.assertNotIn("Dec 2026 planned", en["web_e1_dates"])
        self.assertIn("learned Linux and DevOps through self-study", en["about_p1"])
        self.assertIn("self-hosted Linux environment", en["p1_desc"])

        self.assertEqual(en["e1_dates"], "Jul 2023 – Dec 2026 planned")
        self.assertIn("High-volume electrical wholesale order processing", en["e1_b1"])

    def test_latvian_web_copy_is_natural_and_typographically_clean(self) -> None:
        lv = self.messages["lv"]
        joined = "\n".join(lv.values())
        self.assertIn("2023. g. jūlijs", lv["web_e1_dates"])
        self.assertNotIn("jũlijs", joined)
        self.assertIn("izmantojot skeneru sistēmas", lv["web_e1_b1"])
        self.assertNotIn("pirms/pēc pierādījumiem", lv["p3_ops"])
        self.assertIn("stāvokļa pārbaudēm pirms un pēc atjauninājuma", lv["p3_ops"])

    def test_projects_are_explicitly_framed_as_skill_evidence(self) -> None:
        self.assertEqual(self.messages["en"]["projects_title"], "Projects & proof")
        self.assertEqual(self.messages["de"]["projects_title"], "Projekte & Nachweise")
        self.assertEqual(self.messages["lv"]["projects_title"], "Projekti un pierādījumi")

        for language, messages in self.messages.items():
            evidence = " ".join(
                messages[key]
                for key in (
                    "p7_desc", "p7_ops",
                    "p1_desc", "p1_ops",
                    "p3_desc", "p3_ops",
                    "p2_desc", "p2_ops",
                )
            )
            for technology in ("Docker", "Nginx", "Prometheus", "Bash", "Python"):
                self.assertIn(technology, evidence, f"{language} project proof missing {technology}")


if __name__ == "__main__":
    unittest.main()
