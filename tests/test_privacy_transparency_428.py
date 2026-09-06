import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "de", "lv")


class PrivacyTransparency428Tests(unittest.TestCase):
    def test_public_notice_is_linked_and_uses_only_authorized_location(self) -> None:
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        self.assertIn('id="privacy" class="privacy-panel panel"', html)
        self.assertGreaterEqual(html.count('href="#privacy"'), 2)
        self.assertIn("44319 Dortmund", html)
        for forbidden in ("streetAddress", "postalCode", "Impressum compliant", "full residential"):
            self.assertNotIn(forbidden, html)

    def test_notice_covers_actual_provider_and_security_flows_in_every_language(self) -> None:
        required_keys = (
            "privacy_intro",
            "privacy_openai_body",
            "privacy_turnstile_body",
            "privacy_analytics_body",
            "privacy_local_body",
            "privacy_basis_body",
            "privacy_rights_body",
        )
        for language in LANGUAGES:
            data = json.loads((ROOT / f"content/translations/{language}.json").read_text(encoding="utf-8"))
            for key in required_keys:
                self.assertTrue(data[key].strip(), f"{language}:{key}")
            self.assertIn("44319 Dortmund", data["privacy_intro"])
            self.assertIn("OpenAI", data["privacy_openai_body"])
            self.assertIn("store=false", data["privacy_openai_body"])
            self.assertIn("30", data["privacy_openai_body"])
            self.assertIn("Turnstile", data["privacy_turnstile_body"])
            self.assertIn("Cloudflare Web Analytics", data["privacy_analytics_body"])
            self.assertIn("Telegram", data["privacy_local_body"])
            self.assertNotIn("streetAddress", json.dumps(data, ensure_ascii=False))
            self.assertNotIn("postalCode", json.dumps(data, ensure_ascii=False))

    def test_notice_links_only_to_official_provider_sources(self) -> None:
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        for url in (
            "https://developers.openai.com/api/docs/guides/your-data",
            "https://openai.com/policies/data-processing-addendum/",
            "https://www.cloudflare.com/turnstile-privacy-policy/",
            "https://developers.cloudflare.com/web-analytics/about/",
            "https://www.cloudflare.com/cloudflare-customer-dpa/",
        ):
            self.assertIn(f'href="{url}"', html)

    def test_short_chat_notice_names_openai_without_claiming_provider_zero_retention(self) -> None:
        for language in LANGUAGES:
            data = json.loads((ROOT / f"content/translations/{language}.json").read_text(encoding="utf-8"))
            for key in ("chat_privacy", "chat_privacy_zero", "chat_privacy_retained"):
                value = data[key].lower()
                self.assertIn("openai", value)
                self.assertIn("ip", value)
            self.assertIn("{days}", data["chat_privacy_retained"])
            self.assertNotIn("{days}", data["chat_privacy_zero"])

    def test_privacy_notice_is_not_added_to_print_cv(self) -> None:
        css = (ROOT / "frontend/styles/print.css").read_text(encoding="utf-8")
        self.assertIn(".privacy-panel { display: none !important; }", css)


if __name__ == "__main__":
    unittest.main()
