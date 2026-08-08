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
        raise SystemExit(f"C94_V4_PATCH=FAIL anchor={label} count={count}")
    return text.replace(old, new, 1)


def patch_profile_and_schema() -> None:
    path = ROOT / "content/profile.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    profile["content_version"] = "2026-08-08.2"
    profile["contact"]["email"] = {"value": PUBLIC_EMAIL, "visibility": "public"}
    profile["contact"]["phone"] = {"visibility": "runtime-protected"}
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    path = ROOT / "content/profile.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["properties"]["contact"]["properties"]["email"] = {"$ref": "#/$defs/publicValue"}
    schema["properties"]["contact"]["properties"]["phone"] = {"$ref": "#/$defs/protectedValue"}
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_builder() -> None:
    text = read("scripts/build-content.py")
    text = replace_once(
        text,
        '''    for key in ("email", "phone"):
        entry = require_object(
            contact[key], f"profile.contact.{key}", {"visibility"}
        )
        if entry["visibility"] != "runtime-protected":
            raise ContentError(f"profile.contact.{key} must be runtime-protected")
    for key in ("github", "website"):
''',
        '''    email = require_object(
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
''',
        "builder-validation",
    )
    text = replace_once(
        text,
        '        "Email and phone: available only through the verified contact section on the public CV.",\n',
        '        f"Email: {contact[\'email\'][\'value\']}",\n'
        '        "Phone and WhatsApp: available only through the verified contact section on the public CV.",\n',
        "builder-prompt-contact",
    )
    text = replace_once(
        text,
        '            "- Do not reveal, infer, or guess protected email or phone details; direct contact requests to the verified contact section on the public CV.",\n',
        '            "- The dedicated recruiting email is public and may be provided directly.",\n'
        '            "- Do not reveal, infer, or guess the protected phone number; direct phone or WhatsApp requests to the verified contact section on the public CV.",\n',
        "builder-prompt-rule",
    )
    write("scripts/build-content.py", text)


def patch_index() -> None:
    text = read("frontend/index.html")
    text = replace_once(
        text,
        '<span id="contactEmail" class="contact-masked" aria-label="Email address hidden until verification">an••••@••••••••.net</span>',
        f'<a id="contactEmail" href="mailto:{PUBLIC_EMAIL}">{PUBLIC_EMAIL}</a>',
        "index-public-email",
    )
    text = replace_once(
        text,
        '<span class="contact-reveal-label">Verify to show contact details</span>',
        '<span class="contact-reveal-label">Verify to show phone / WhatsApp</span>',
        "index-contact-button",
    )
    write("frontend/index.html", text)


def patch_app() -> None:
    text = read("frontend/app.mjs")
    text = replace_once(text, '  if (!button) return;\n', '  if (!button) return null;\n', "app-null-contact")
    text = replace_once(
        text,
        '  button.addEventListener("click", activate);\n}\n\nasync function init() {',
        '''  button.addEventListener("click", activate);
  return activate;
}

function requestedWhatsAppContact() {
  try {
    return new URL(window.location.href).searchParams.get("contact") === "whatsapp";
  } catch {
    return false;
  }
}

async function init() {''',
        "app-contact-return",
    )
    text = replace_once(
        text,
        '  enhanceSkillIcons();\n  installLazyContact(languageController);\n\n  const stats = createStatsController(languageController);',
        '''  enhanceSkillIcons();
  const activateContact = installLazyContact(languageController);
  if (requestedWhatsAppContact()) await activateContact?.();

  const stats = createStatsController(languageController);''',
        "app-contact-init",
    )
    write("frontend/app.mjs", text)


def patch_contact_controller() -> None:
    text = read("frontend/features/contact.mjs")
    text = replace_once(
        text,
        'export function contactPayloadIsValid(payload) {',
        '''export function contactPurpose(windowLike = globalThis.window) {
  try {
    return new URL(windowLike.location.href).searchParams.get("contact") === "whatsapp"
      ? "whatsapp"
      : "phone";
  } catch {
    return "phone";
  }
}

export function contactPayloadIsValid(payload) {''',
        "contact-purpose",
    )
    text = replace_once(
        text,
        '''  const message = (key) => {
    const value = languageController.messages?.[key];
    return typeof value === "string" ? value : "";
  };
''',
        '''  const purpose = contactPurpose(windowLike);
  const message = (key) => {
    const value = languageController.messages?.[key];
    return typeof value === "string" ? value : "";
  };
''',
        "contact-purpose-state",
    )
    text = replace_once(
        text,
        '''    const email = root.querySelector("#contactEmail");
    const phone = root.querySelector("#contactPhone");
    if (label && !button.dataset.locked) {
      label.textContent = message("contact_reveal");
    }
    if (email && email.dataset.revealed !== "true") {
      email.setAttribute("aria-label", message("contact_email_hidden"));
    }
''',
        '''    const phone = root.querySelector("#contactPhone");
    if (label && !button.dataset.locked) {
      label.textContent = message(
        purpose === "whatsapp" ? "contact_whatsapp_verify" : "contact_reveal"
      );
    }
''',
        "contact-refresh-copy",
    )
    text = replace_once(
        text,
        '''    const email = root.querySelector("#contactEmail");
    const phone = root.querySelector("#contactPhone");
    const emailLink = email ? revealLink(root, email, payload.email, `mailto:${payload.email}`) : null;
    const whatsappNumber = payload.phone_uri.slice(1);
    const phoneLink = phone ? revealLink(root, phone, payload.phone, `https://wa.me/${whatsappNumber}`) : null;
    button.hidden = true;
    mount.hidden = true;
    setStatus(root, message("contact_success"), "success");
    windowLike.setTimeout(() => (emailLink || phoneLink)?.focus(), 0);
    return true;
''',
        '''    const phone = root.querySelector("#contactPhone");
    const whatsappNumber = payload.phone_uri.slice(1);
    const whatsappUrl = `https://wa.me/${whatsappNumber}`;
    button.hidden = true;
    mount.hidden = true;
    setStatus(root, message("contact_success"), "success");
    if (purpose === "whatsapp") {
      windowLike.setTimeout(() => windowLike.location.assign(whatsappUrl), 0);
      return true;
    }
    const phoneLink = phone ? revealLink(root, phone, payload.phone, whatsappUrl) : null;
    windowLike.setTimeout(() => phoneLink?.focus(), 0);
    return true;
''',
        "contact-submit",
    )
    text = replace_once(
        text,
        '  return { start, refreshCopy };\n',
        '  return { start, refreshCopy, purpose };\n',
        "contact-return-purpose",
    )
    write("frontend/features/contact.mjs", text)


def patch_translations() -> None:
    updates = {
        "en": {"contact_reveal": "Verify to show phone / WhatsApp", "contact_whatsapp_verify": "Verify to open WhatsApp", "contact_success": "Contact verified."},
        "de": {"contact_reveal": "Prüfen, um Telefon / WhatsApp anzuzeigen", "contact_whatsapp_verify": "Prüfen, um WhatsApp zu öffnen", "contact_success": "Kontakt bestätigt."},
        "lv": {"contact_reveal": "Pārbaudīt, lai parādītu tālruni / WhatsApp", "contact_whatsapp_verify": "Pārbaudīt, lai atvērtu WhatsApp", "contact_success": "Kontakts apstiprināts."},
    }
    keysets = []
    for language, changes in updates.items():
        path = ROOT / "content" / "translations" / f"{language}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(changes)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        keysets.append(set(data))
    if not all(keys == keysets[0] for keys in keysets[1:]):
        raise SystemExit("C94_V4_PATCH=FAIL anchor=translation-keys")


def patch_tests() -> None:
    text = read("tests/frontend.test.mjs")
    text = replace_once(
        text,
        'import { contactPayloadIsValid } from "../frontend/features/contact.mjs";',
        'import { contactPayloadIsValid, contactPurpose } from "../frontend/features/contact.mjs";',
        "frontend-test-import",
    )
    text = replace_once(text, '    "contact_reveal",\n', '    "contact_reveal",\n    "contact_whatsapp_verify",\n', "frontend-test-key")
    marker = '''  assert.equal(
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
  assert.equal(
    contactPurpose({ location: { href: "https://rozkalns.net/?contact=whatsapp" } }),
    "whatsapp"
  );
});'''
    text = replace_once(text, marker, replacement, "frontend-test-purpose")
    write("tests/frontend.test.mjs", text)

    text = read("tests/browser-smoke.mjs")
    turnstile = '''    await cdp.evaluate(`(() => {
      window.turnstile = {'''
    pre = f'''    assert.equal(
      await cdp.evaluate(`document.querySelector('#contactEmail')?.getAttribute('href')`),
      "mailto:{PUBLIC_EMAIL}"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#contactPhone')?.tagName`),
      "SPAN"
    );
'''
    text = replace_once(text, turnstile, pre + turnstile, "browser-preconditions")
    text = replace_once(text, '      "keyboard contact verification focus transfer"\n', '      "keyboard WhatsApp phone verification focus transfer"\n', "browser-focus-label")
    text = replace_once(text, '      "mailto:test@example.invalid"\n', '      "https://wa.me/491234567890"\n', "browser-focus-url")
    write("tests/browser-smoke.mjs", text)

    text = read("tests/test_contact_markup.py")
    pattern = re.compile(r"    def test_initial_html_does_not_embed_contact_channels\(self\) -> None:\n.*?\n    def test_contact_config_has_no_embedded_contact_fallbacks", re.DOTALL)
    replacement = f'''    def test_initial_html_exposes_public_email_but_not_phone(self) -> None:
        index = (ROOT / "html" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="mailto:{PUBLIC_EMAIL}"', index)
        self.assertIn('>{PUBLIC_EMAIL}</a>', index)
        self.assertNotRegex(index, r'(?i)href=["\\\'](?:tel:|https://wa\\.me/[0-9])')
        self.assertIn('id="contactPhone"', index)
        self.assertIn('class="contact-masked"', index)
        self.assertIn('id="contactReveal"', index)
        self.assertIn('id="turnstileMount"', index)

    def test_contact_config_has_no_embedded_contact_fallbacks'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"C94_V4_PATCH=FAIL anchor=markup-test count={count}")
    write("tests/test_contact_markup.py", text)

    privacy = f'''from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CurrentContactPolicyTests(unittest.TestCase):
    def test_canonical_email_is_public_and_phone_is_runtime_protected(self) -> None:
        profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["contact"]["email"], {{"value": "{PUBLIC_EMAIL}", "visibility": "public"}})
        self.assertEqual(profile["contact"]["phone"], {{"visibility": "runtime-protected"}})

    def test_assistant_exposes_email_but_not_phone(self) -> None:
        prompt = (ROOT / "bot/system_prompt.txt").read_text(encoding="utf-8")
        self.assertIn("Email: {PUBLIC_EMAIL}", prompt)
        self.assertIn("Phone and WhatsApp: available only through", prompt)
        self.assertNotRegex(prompt, r"Phone:\\s*\\+[0-9]")

    def test_public_frontend_has_no_direct_numbered_contact_target(self) -> None:
        index = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        app = (ROOT / "frontend/app.mjs").read_text(encoding="utf-8")
        contact = (ROOT / "frontend/features/contact.mjs").read_text(encoding="utf-8")
        self.assertIn("mailto:{PUBLIC_EMAIL}", index)
        self.assertIn("?contact=whatsapp", app)
        self.assertNotRegex(index + app + contact, r"https://wa\\.me/[0-9]")
        self.assertNotRegex(index + app + contact, r"tel:\\+[0-9]")

    def test_bootstrap_keeps_personal_author_fallback_removed(self) -> None:
        bootstrap = (ROOT / "scripts/bootstrap-github.sh").read_text(encoding="utf-8")
        self.assertIn("GIT_AUTHOR_EMAIL", bootstrap)
        self.assertNotRegex(bootstrap, r"GIT_AUTHOR_EMAIL=.*@")
        self.assertNotIn('git config user.email "{PUBLIC_EMAIL}"', bootstrap)


if __name__ == "__main__":
    unittest.main()
'''
    write("tests/test_current_contact_privacy.py", privacy)


def patch_docs() -> None:
    text = read("docs/PUBLIC_READINESS.md")
    text = text.replace(
        "- [x] Remove personal contact values from the current tracked source/tests; the Turnstile reveal flow now reads contact values only from runtime environment variables.",
        "- [ ] #94 — dedicated recruiting email is intentionally public; phone remains runtime-protected; one-page public PDFs use a protected-site WhatsApp QR. Final merge/deploy evidence is pending.",
        1,
    )
    text = text.replace(
        "- Contact values are runtime configuration; missing `CONTACT_*` values fail closed instead of falling back to embedded personal data.",
        "- `andris@rozkalns.net` is intentionally public for recruiting. Phone values remain runtime configuration. Public PDFs use a QR to the verified-site WhatsApp flow instead of printing the phone number.",
        1,
    )
    write("docs/PUBLIC_READINESS.md", text)


def main() -> int:
    patch_profile_and_schema()
    patch_builder()
    patch_index()
    patch_app()
    patch_contact_controller()
    patch_translations()
    patch_tests()
    patch_docs()
    print("C94_V4_PATCH=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
