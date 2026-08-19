# Canonical CV content workflow

The public CV, assistant knowledge, translations, and PDF freshness state must
not be edited as independent copies. The authoritative human-maintained sources
are:

- `content/profile.json` — public professional facts, structured records, and runtime-protected contact-channel metadata;
- `content/profile.schema.json` — documented shape and field intent;
- `content/skill-labels.json` — localized EN/DE/LV display labels keyed by canonical skill concepts;
- `content/translations/en.json`, `de.json`, and `lv.json` — localized page copy.

Everything else listed below is generated or validated against these sources.
`content/skill-labels.json` is human-maintained source, not generated output.

## Editing facts

1. Create an issue and isolated branch.
2. Edit `content/profile.json`; preserve stable IDs for existing experience,
   education, and project records.
3. Change `content_version` whenever public facts change.
4. If canonical `skills` membership or a skill concept name changes, update
   `content/skill-labels.json` so its concept set matches `content/profile.json`
   exactly and every concept has non-empty `en`, `de`, and `lv` labels.
5. Update all three translation files when the visible wording changes. Their
   key sets must remain identical. For `skills_*_items`, preserve canonical
   profile membership/order and render the localized labels from
   `content/skill-labels.json`.
6. Run:

   ```bash
   python3 scripts/build-content.py --write
   python3 scripts/sync-system-prompt.py --write
   ```

   The first command intentionally refuses to accept stale PDFs. This is the
   signal that the PDF documents must be regenerated and reviewed.

## Generated outputs

The builder deterministically produces and checks:

- SHA-256-fingerprinted files in `html/i18n/`;
- the fingerprinted CV application module and its references in HTML, CI, and
  Node tests;
- `bot/system_prompt.txt` from public canonical profile facts, excluding runtime-protected email and phone values;
- the marked generated `SYSTEM_PROMPT` block inside `bot/app.py`;
- `content/pdf-manifest.json`, which binds each committed PDF and the complete
  canonical source set to exact SHA-256 values.

Do not edit these generated regions directly. `scripts/validate-source.sh`
runs both generators in `--check` mode and rejects drift, extra stale hashed
assets, missing generated files, or an out-of-date PDF manifest.

## PDF release gate

The builder does not create or visually validate PDF layout. When canonical
content changes:

1. regenerate English, German, and Latvian PDFs from the approved content;
2. open every PDF and verify text, line wrapping, dates, links, page breaks,
   language, and accessibility metadata;
3. confirm runtime-protected email/phone values and contact links are absent from
   every PDF, while public GitHub, website, role, availability, work history,
   projects, skills, and education remain correct;
4. only after that review run:

   ```bash
   python3 scripts/build-content.py --write --accept-pdfs
   python3 scripts/sync-system-prompt.py --write
   python3 scripts/build-content.py --check
   python3 scripts/sync-system-prompt.py --check
   ```

`--accept-pdfs` records the current committed PDF hashes; it does not claim that
a review happened. The reviewer and evidence belong in the pull request.

For the initial migration, the manifest may snapshot the previously published
PDF files without altering them. Record that explicitly as an existing-artifact
snapshot, not as a new visual review.

## Review checklist

A content pull request is ready only when:

- profile validation and unique-ID checks pass;
- EN/DE/LV keys match;
- the skill-label concept set matches canonical `profile.json` skills exactly,
  every concept has EN/DE/LV labels, and localized `skills_*_items` follow
  canonical membership/order through those labels;
- generated files are committed with no stale fingerprints;
- the assistant prompt contains only public canonical facts and directs email/phone requests to the verified contact section;
- the three PDFs have a current manifest and documented review/snapshot basis;
- Python, Node, browser, nginx, image build, and deploy contract CI are green;
- no production deploy is performed until the final merged SHA is selected.
