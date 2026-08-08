# Canonical CV content workflow

The public CV, assistant knowledge, translations, and PDF freshness state must
not be edited as independent copies. The authoritative human-maintained sources
are:

- `content/profile.json` — public professional facts plus contact visibility policy;
- `content/profile.schema.json` — documented shape and field intent;
- `content/translations/en.json`, `de.json`, and `lv.json` — localized page copy.

Everything else listed below is generated or validated against these sources.

## Protected contact boundary

Email and phone are **not canonical public values**. `content/profile.json` must
contain only `visibility: verified-runtime` for those two channels. The real
values exist only in host-side runtime configuration and are returned by the
server-side Turnstile contact-reveal flow after successful verification.

The canonical profile may still contain intentionally public channels such as
the GitHub profile and website URL.

Do not put the real email address or phone number into:

- `content/profile.json`;
- `bot/system_prompt.txt`;
- the generated `SYSTEM_PROMPT` block in `bot/app.py`;
- frontend source or generated HTML;
- tests, fixtures, CI summaries or GitHub evidence.

The assistant prompt must direct visitors to the verified contact section
instead of reproducing those contact values.

## Editing facts

1. Create an issue and isolated branch.
2. Edit `content/profile.json`; preserve stable IDs for existing experience,
   education, and project records.
3. Change `content_version` whenever public facts or contact policy change.
4. Update all three translation files when the visible wording changes. Their
   key sets must remain identical.
5. Run:

   ```bash
   python3 scripts/build-content.py --write
   python3 scripts/sync-system-prompt.py --write
   ```

   The first command intentionally refuses to accept stale PDFs unless their
   contact/privacy policy has been resolved explicitly.

## Generated outputs

The builder deterministically produces and checks:

- SHA-256-fingerprinted files in `html/i18n/`;
- the fingerprinted CV application module and its references in HTML, CI, and
  Node tests;
- `bot/system_prompt.txt` from canonical profile facts and contact policy;
- the marked generated `SYSTEM_PROMPT` block inside `bot/app.py`;
- `content/pdf-manifest.json`, which records exact PDF hashes and their explicit
  contact/privacy review state.

Do not edit generated regions directly. `scripts/validate-source.sh` runs both
generators in `--check` mode and rejects drift, extra stale hashed assets,
missing generated files, or an invalid PDF manifest state.

## PDF privacy and release gate

PDFs are public static artifacts when committed under `html/`. They therefore
cannot rely on the interactive Turnstile reveal boundary.

During #94 the existing PDF files are intentionally marked
`legacy-public-contact-pending-owner-decision`. In this pending state:

- their exact hashes are still validated;
- `source_sha256` is deliberately `null` so the manifest does not falsely claim
  that the legacy PDFs match the new runtime-protected contact model;
- the state blocks #94 completion and must not be silently converted to an
  accepted state.

After an explicit owner decision, regenerate/review English, German and Latvian
PDFs and choose exactly one reviewed policy:

- `verified-no-protected-contact` — the PDF files do not embed the protected
  email/phone channels; or
- `owner-approved-public-contact` — the owner has explicitly decided that the
  PDF copies of those contact channels are intentionally public.

Only after that review run:

```bash
python3 scripts/build-content.py --write --accept-pdfs \
  --pdf-contact-policy <reviewed-policy>
python3 scripts/sync-system-prompt.py --write
python3 scripts/build-content.py --check
python3 scripts/sync-system-prompt.py --check
```

`--accept-pdfs` records the current committed PDF hashes and binds them to the
current canonical source only after an explicit non-pending privacy policy has
been selected. The reviewer and evidence belong in the pull request.

## Review checklist

A content pull request is ready only when:

- profile validation and unique-ID checks pass;
- protected email/phone channels contain no tracked values;
- EN/DE/LV keys match;
- generated files are committed with no stale fingerprints;
- the assistant prompt contains only public canonical facts plus the verified
  contact policy;
- the three PDFs have a non-pending owner-reviewed contact policy before #94 is
  considered complete;
- Python, Node, browser, nginx, image build, and deploy contract CI are green;
- no production deploy is performed until the final merged SHA is selected.
