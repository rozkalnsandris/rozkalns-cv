#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_EMAIL = "andris@rozkalns.net"
PROTECTED_URL = "https://rozkalns.net/?contact=whatsapp"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"C94_PATCH=FAIL anchor={label} count={count}")
    return text.replace(old, new, 1)


def patch_builder() -> None:
    text = read("scripts/build-content.py")
    old = '''    for key in ("email", "phone"):
        entry = require_object(
            contact[key], f"profile.contact.{key}", {"visibility"}
        )
        if entry["visibility"] != "runtime-protected":
            raise ContentError(f"profile.contact.{key} must be runtime-protected")
    for key in ("github", "website"):
'''
    new = '''    email = require_object(
        contact["email"], "profile.contact.email", {"value", "visibility"}
    )
    require_text(email["value"], "profile.contact.email.value", 3)
    if email["visibility"] != "public":
        raise ContentError("profile.contact.email must be public")
    phone = require_object(
        contact["phone"], "profile.contact.phone", {"visibility"}
    )
    if phone["visibility"] != "runtime-protected":
        raise ContentError("profile.contact.phone must be runtime-protected")
    for key in ("github", "website"):
'''
    text = replace_once(text, old, new, "builder-contact-validation")
    text = replace_once(
        text,
        '        "Email and phone: available only through the verified contact section on the public CV.",\n',
        '        f"Email: {contact[\'email\'][\'value\']}",\n'
        '        "Phone and WhatsApp: available only through the verified contact section on the public CV.",\n',
        "builder-contact-prompt",
    )
    text = replace_once(
        text,
        '            "- Do not reveal, infer, or guess protected email or phone details; direct contact requests to the verified contact section on the public CV.",\n',
        '            "- The dedicated recruiting email is public and may be provided directly.",\n'
        '            "- Do not reveal, infer, or guess the protected phone number; direct phone or WhatsApp requests to the verified contact section on the public CV.",\n',
        "builder-contact-rule",
    )
    write("scripts/build-content.py", text)


def patch_frontend_index() -> None:
    text = read("frontend/index.html")
    text = replace_once(
        text,
        '<span id="contactEmail" class="contact-masked" aria-label="Email address hidden until verification">an••••@••••••••.net</span>',
        f'<a id="contactEmail" href="mailto:{PUBLIC_EMAIL}">{PUBLIC_EMAIL}</a>',
        "frontend-public-email",
    )
    text = replace_once(
        text,
        '<span class="contact-reveal-label">Verify to show contact details</span>',
        '<span class="contact-reveal-label">Verify to show phone number</span>',
        "frontend-contact-button",
    )
    write("frontend/index.html", text)


def patch_backend() -> None:
    text = read("bot/app.py")
    old = '''    response = jsonify(
        email=CONTACT_CONFIG.email,
        phone=CONTACT_CONFIG.phone_display,
        phone_uri=CONTACT_CONFIG.phone_uri,
    )
'''
    new = '''    try:
        whatsapp_url = CONTACT_CONFIG.whatsapp_url
    except ContactVerificationError as error:
        app.logger.error("verified contact target failed: %s", type(error).__name__)
        return jsonify(error="Contact verification is temporarily unavailable."), 503

    response = jsonify(
        email=CONTACT_CONFIG.email,
        phone=CONTACT_CONFIG.phone_display,
        phone_uri=CONTACT_CONFIG.phone_uri,
        whatsapp_url=whatsapp_url,
    )
'''
    text = replace_once(text, old, new, "backend-contact-response")
    write("bot/app.py", text)


def patch_translations() -> None:
    updates = {
        "en": {
            "contact_reveal": "Verify to show phone number",
            "contact_whatsapp_verify": "Verify to open WhatsApp",
            "contact_success": "Contact verified.",
        },
        "de": {
            "contact_reveal": "Prüfen, um die Telefonnummer anzuzeigen",
            "contact_whatsapp_verify": "Prüfen, um WhatsApp zu öffnen",
            "contact_success": "Kontakt bestätigt.",
        },
        "lv": {
            "contact_reveal": "Pārbaudīt, lai parādītu tālruni",
            "contact_whatsapp_verify": "Pārbaudīt, lai atvērtu WhatsApp",
            "contact_success": "Kontakts apstiprināts.",
        },
    }
    keysets = []
    for language, changes in updates.items():
        path = ROOT / "content" / "translations" / f"{language}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(changes)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        keysets.append(set(data))
    if not all(keys == keysets[0] for keys in keysets[1:]):
        raise SystemExit("C94_PATCH=FAIL anchor=translation-keyset")


def patch_frontend_tests() -> None:
    text = read("tests/frontend.test.mjs")
    text = replace_once(
        text,
        'import { contactPayloadIsValid } from "../frontend/features/contact.mjs";',
        'import { contactPayloadIsValid, contactPurpose, whatsappUrlIsValid } from "../frontend/features/contact.mjs";',
        "frontend-test-import",
    )
    text = replace_once(
        text,
        '    "contact_reveal",\n',
        '    "contact_reveal",\n    "contact_whatsapp_verify",\n',
        "frontend-test-i18n-key",
    )
    anchor = '''  assert.equal(
    contactPayloadIsValid({
      email: "not-an-email",
      phone: "123",
      phone_uri: "javascript:alert(1)"
    }),
    false
  );
});'''
    replacement = '''  assert.equal(
    contactPayloadIsValid({
      email: "not-an-email",
      phone: "123",
      phone_uri: "javascript:alert(1)"
    }),
    false
  );
  assert.equal(whatsappUrlIsValid("https://wa.me/49123456789"), true);
  assert.equal(whatsappUrlIsValid("javascript:alert(1)"), false);
  assert.equal(
    contactPurpose({ location: { href: "https://rozkalns.net/?contact=whatsapp" } }),
    "whatsapp"
  );
});'''
    text = replace_once(text, anchor, replacement, "frontend-test-contact-policy")
    write("tests/frontend.test.mjs", text)


def patch_browser_smoke() -> None:
    text = read("tests/browser-smoke.mjs")
    fixture = '          phone_uri: "+491234567890"\n'
    text = replace_once(
        text,
        fixture,
        '          phone_uri: "+491234567890",\n'
        '          whatsapp_url: "https://wa.me/491234567890"\n',
        "browser-contact-fixture",
    )
    turnstile = '''    await cdp.evaluate(`(() => {
      window.turnstile = {'''
    preconditions = f'''    assert.equal(
      await cdp.evaluate(`document.querySelector('#contactEmail')?.getAttribute('href')`),
      "mailto:{PUBLIC_EMAIL}"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#contactPhone')?.tagName`),
      "SPAN"
    );
'''
    text = replace_once(
        text, turnstile, preconditions + turnstile, "browser-contact-preconditions"
    )
    text = replace_once(
        text,
        '      "keyboard contact verification focus transfer"\n',
        '      "keyboard phone verification focus transfer"\n',
        "browser-contact-focus-label",
    )
    text = replace_once(
        text,
        '      "mailto:test@example.invalid"\n',
        '      "tel:+491234567890"\n',
        "browser-contact-focus-href",
    )
    write("tests/browser-smoke.mjs", text)


def patch_contact_markup_test() -> None:
    text = read("tests/test_contact_markup.py")
    pattern = re.compile(
        r"    def test_initial_html_does_not_embed_contact_channels\(self\) -> None:\n.*?\n    def test_contact_config_has_no_embedded_contact_fallbacks",
        re.DOTALL,
    )
    replacement = f'''    def test_initial_html_exposes_public_email_but_not_phone(self) -> None:
        index = (ROOT / "html" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="mailto:{PUBLIC_EMAIL}"', index)
        self.assertIn('>{PUBLIC_EMAIL}</a>', index)
        self.assertNotRegex(index, r'(?i)href=["\\\']tel:')
        self.assertIn('id="contactPhone"', index)
        self.assertIn('class="contact-masked"', index)
        self.assertIn('id="contactReveal"', index)
        self.assertIn('id="turnstileMount"', index)

    def test_contact_config_has_no_embedded_contact_fallbacks'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"C94_PATCH=FAIL anchor=contact-markup count={count}")
    write("tests/test_contact_markup.py", text)


def patch_current_privacy_test() -> None:
    text = f'''from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurrentContactPolicyTests(unittest.TestCase):
    def test_canonical_email_is_public_and_phone_is_runtime_protected(self) -> None:
        profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["contact"]["email"]["visibility"], "public")
        self.assertEqual(profile["contact"]["email"]["value"], "{PUBLIC_EMAIL}")
        self.assertEqual(profile["contact"]["phone"], {{"visibility": "runtime-protected"}})

        schema = json.loads((ROOT / "content/profile.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["contact"]["properties"]["email"], {{"$ref": "#/$defs/publicValue"}})
        self.assertEqual(schema["properties"]["contact"]["properties"]["phone"], {{"$ref": "#/$defs/protectedValue"}})

    def test_generated_assistant_knows_public_email_but_not_phone(self) -> None:
        prompt = (ROOT / "bot/system_prompt.txt").read_text(encoding="utf-8")
        app = (ROOT / "bot/app.py").read_text(encoding="utf-8")
        self.assertIn("Email: {PUBLIC_EMAIL}", prompt)
        self.assertIn("Phone and WhatsApp: available only through", prompt)
        self.assertNotRegex(prompt, r"Phone:\\s*\\+[0-9]")
        self.assertIn("Email: {PUBLIC_EMAIL}", app)
        self.assertNotRegex(app, r"Phone:\\s*\\+[0-9]")

    def test_public_frontend_has_email_but_no_numbered_whatsapp_target(self) -> None:
        source = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")
        contact = (ROOT / "frontend/features/contact.mjs").read_text(encoding="utf-8")
        self.assertIn("mailto:{PUBLIC_EMAIL}", source)
        self.assertIn('searchParams.get("contact") === "whatsapp"', app)
        self.assertNotRegex(source + app, r"wa\\.me/[0-9]")
        self.assertNotRegex(source + app, r"tel:\\+[0-9]")
        self.assertNotRegex(contact, r"https://wa\\.me/[0-9]")

    def test_bootstrap_git_author_has_no_personal_email_fallback(self) -> None:
        bootstrap = (ROOT / "scripts/bootstrap-github.sh").read_text(encoding="utf-8")
        self.assertIn("GIT_AUTHOR_EMAIL", bootstrap)
        self.assertNotRegex(bootstrap, r"GIT_AUTHOR_EMAIL=.*@")
        self.assertNotIn('git config user.email "{PUBLIC_EMAIL}"', bootstrap)


if __name__ == "__main__":
    unittest.main()
'''
    write("tests/test_current_contact_privacy.py", text)


def patch_contact_test() -> None:
    text = read("tests/test_contact.py")
    text = replace_once(
        text,
        '                "phone_uri": "+49123456789",\n',
        '                "phone_uri": "+49123456789",\n'
        '                "whatsapp_url": "https://wa.me/49123456789",\n',
        "python-contact-response",
    )
    text = replace_once(
        text,
        '        self.assertNotIn("+49123456789", body)\n',
        '        self.assertNotIn("+49123456789", body)\n'
        '        self.assertNotIn("wa.me", body)\n',
        "python-contact-fail-closed",
    )
    write("tests/test_contact.py", text)


def patch_docs() -> None:
    readiness = read("docs/PUBLIC_READINESS.md")
    readiness = readiness.replace(
        "- [x] Remove personal contact values from the current tracked source/tests; the Turnstile reveal flow now reads contact values only from runtime environment variables.",
        "- [ ] #94 — keep the dedicated recruiting email public while protecting phone/WhatsApp behind server-side verification; final merge/deploy evidence is still pending.",
        1,
    )
    readiness = readiness.replace(
        "- Contact values are runtime configuration; missing `CONTACT_*` values fail closed instead of falling back to embedded personal data.",
        "- `andris@rozkalns.net` is intentionally public for recruiting. Phone values remain runtime configuration; missing `CONTACT_*` values fail closed instead of falling back to embedded personal data. Public PDFs use a QR to the verified-site WhatsApp flow rather than printing the phone number.",
        1,
    )
    write("docs/PUBLIC_READINESS.md", readiness)

    authoring = read("docs/CONTENT_AUTHORING.md")
    authoring = authoring.replace(
        "`content/profile.json` — public professional facts, structured records, and runtime-protected contact-channel metadata;",
        "`content/profile.json` — public professional facts, the intentionally public recruiting email, and runtime-protected phone-channel metadata;",
        1,
    )
    authoring = authoring.replace(
        "`bot/system_prompt.txt` from public canonical profile facts, excluding runtime-protected email and phone values;",
        "`bot/system_prompt.txt` from public canonical profile facts, including the recruiting email while excluding the runtime-protected phone value;",
        1,
    )
    authoring = authoring.replace(
        "the assistant prompt contains only public canonical facts and directs email/phone requests to the verified contact section;",
        "the assistant prompt may provide the public recruiting email but directs phone/WhatsApp requests to the verified contact section;",
        1,
    )
    write("docs/CONTENT_AUTHORING.md", authoring)


def main() -> int:
    profile = json.loads(read("content/profile.json"))
    if profile["contact"]["email"] != {"value": PUBLIC_EMAIL, "visibility": "public"}:
        raise SystemExit("C94_PATCH=FAIL anchor=canonical-email")
    if profile["contact"]["phone"] != {"visibility": "runtime-protected"}:
        raise SystemExit("C94_PATCH=FAIL anchor=canonical-phone")
    patch_builder()
    patch_frontend_index()
    patch_backend()
    patch_translations()
    patch_frontend_tests()
    patch_browser_smoke()
    patch_contact_markup_test()
    patch_current_privacy_test()
    patch_contact_test()
    patch_docs()
    print("C94_SOURCE_POLICY_PATCH=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())