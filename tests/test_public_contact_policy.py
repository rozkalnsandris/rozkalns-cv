from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contact = load_module("cv_contact_policy", ROOT / "bot" / "contact.py")


class PublicContactPolicyTests(unittest.TestCase):
    def test_public_email_and_runtime_phone_are_structurally_separated(self) -> None:
        profile = json.loads(
            (ROOT / "content" / "profile.json").read_text(encoding="utf-8")
        )
        self.assertEqual(profile["contact"]["email"]["visibility"], "public")
        self.assertIn("@", profile["contact"]["email"]["value"])
        self.assertEqual(
            profile["contact"]["phone"], {"visibility": "verified-runtime"}
        )

    def test_public_frontend_module_contains_no_direct_whatsapp_number(self) -> None:
        module = (ROOT / "frontend" / "public-contact.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("PUBLIC_EMAIL", module)
        self.assertIn("?contact=whatsapp", module)
        self.assertNotIn("wa.me/", module)
        self.assertNotIn("CONTACT_PHONE", module)

    def test_qr_asset_is_tracked_without_direct_whatsapp_target(self) -> None:
        qr = (ROOT / "frontend" / "media" / "whatsapp-contact-qr.svg").read_text(
            encoding="utf-8"
        )
        self.assertIn("WhatsApp contact QR code", qr)
        self.assertNotIn("wa.me/", qr)
        self.assertNotRegex(qr, r"\+[0-9]{8,15}")

    def test_runtime_phone_is_only_converted_to_whatsapp_after_configuration(self) -> None:
        config = contact.ContactConfig(
            site_key="site",
            secret_key="secret",
            email="person@example.com",
            phone_display="+49 123 456789",
            phone_uri="+49123456789",
            hostnames=frozenset({"example.com"}),
        )
        self.assertEqual(config.whatsapp_url, "https://wa.me/49123456789")


if __name__ == "__main__":
    unittest.main()
