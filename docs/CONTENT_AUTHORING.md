# Canonical CV content workflow

The public CV, assistant knowledge, translations, and PDF freshness state must
not be edited as independent copies. The authoritative human-maintained sources
are:

- `content/profile.json` — public professional facts plus contact visibility policy;
- `content/profile.schema.json` — documented shape and field intent;
- `content/translations/en.json`, `de.json`, and `lv.json` — localized page copy.

Everything else listed below is generated or validated against these sources.

## Contact boundary

The recruiting email `andris@rozkalns.net` is an **intentionally public CV
contact**. It is allowed in canonical public content, the assistant knowledge,
the rendered site and public PDFs.

The phone number is **not a canonical public value**. `content/profile.json`
contains only `visibility: verified-runtime` for the phone channel. The real
phone values exist only in host-side runtime configuration and are returned by
the server-side Turnstile contact flow after successful verification.

Public PDFs provide a QR-based WhatsApp/phone path without embedding the phone
number. The tracked QR payload is only:

`https://rozkalns.net/?contact=whatsapp`

After the visitor passes server-side Turnstile verification, the backend derives
the `wa.me` target from runtime `CONTACT_PHONE_URI`. The phone number and direct
WhatsApp target must never be encoded in the tracked QR asset or generated
public frontend source.

Do not put the real phone number or a direct `wa.me/<number>` target into:

- `content/profile.json`;
- `bot/system_prompt.txt` or generated assistant knowledge;
- frontend source, generated HTML or QR payloads;
- PDF text or PDF link annotations;
- tests, fixtures, CI summaries or GitHub evidence, except synthetic test values.

## Editing facts

1. Create an issue and isolated branch.
2. Edit `content/profile.json`; preserve stable IDs for existing experience,
   education, and project records.
3. Change `content_version` whenever public facts or contact policy change.
4. Update all three translation files when visible wording changes. Their key
   sets must remain identical.
5. Run:

   ```bash
   python3 scripts/build-content.py --write
   python3 scripts/sync-system-prompt.py --write
   ```

   The first command intentionally refuses to accept stale PDFs unless their
   contact/privacy policy has been resolved explicitly.

## Generated outputs

The builder deterministically produces and checks:

- `frontend/public-contact.mjs`, containing only the public email and the
  protected-site WhatsApp entry URL;
- SHA-256-fingerprinted frontend assets in `html/assets/` and `html/i18n/`;
- the fingerprinted CV application module and its references in HTML, CI, and
  Node tests;
- `bot/system_prompt.txt` from canonical profile facts and contact policy;
- the marked generated `SYSTEM_PROMPT` block inside `bot/app.py`;
- `content/pdf-manifest.json`, which records exact PDF hashes and their explicit
  contact/privacy review state.

Do not edit generated regions directly. `scripts/validate-source.sh` runs the
content/prompt generators in `--check` mode and rejects drift, extra stale
hashed assets, missing generated files, or an invalid PDF manifest state.

## PDF privacy and release gate

PDFs are public static artifacts when committed under `html/`. The approved
public PDF contact policy is:

- public recruiting email is visible and clickable;
- raw phone text and `tel:` annotations are absent;
- direct `wa.me/<number>` annotations are absent;
- a WhatsApp-marked QR is present and decodes only to
  `https://rozkalns.net/?contact=whatsapp`;
- the scanned path performs server-side Turnstile verification before the
  runtime phone number is converted into a WhatsApp target.

The accepted manifest policy for this model is:

`verified-public-email-protected-phone`

Regenerate English, German and Latvian PDFs from the current deterministic
frontend, visually inspect every page, verify text/link policy, and decode the
QR from a rasterized PDF page before accepting the PDF hashes.

Only after that review run:

```bash
python3 scripts/build-content.py --write --accept-pdfs \
  --pdf-contact-policy verified-public-email-protected-phone
python3 scripts/sync-system-prompt.py --write
python3 scripts/build-content.py --check
python3 scripts/sync-system-prompt.py --check
```

`--accept-pdfs` records the current PDF hashes and binds them to the current
canonical source only after the explicit reviewed policy is selected. The
reviewer and evidence belong in the pull request.

## Review checklist

A content pull request is ready only when:

- profile validation and unique-ID checks pass;
- recruiting email is intentionally public and phone remains runtime-only;
- EN/DE/LV translation key sets match;
- generated files are committed with no stale fingerprints;
- assistant knowledge may expose the recruiting email but never the phone;
- all three PDFs visually pass with no clipping/overlap;
- all three PDFs contain the public email, omit direct phone/WhatsApp-number
  links, and their QR decodes to the protected-site URL;
- Python, Node, browser, nginx, image build, secret scan and deploy-contract CI
  are green;
- no production deploy is performed until the final merged SHA is selected.
