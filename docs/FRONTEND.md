# CV frontend architecture — source contract

The public CV uses semantic HTML, modular CSS and browser ES modules. Vite is
build-time tooling only: there is no production Node.js frontend server or
runtime Vite build. GitHub source and an installed RPi5 release are separate
kinds of evidence.

## Authored source and generated deployment files

- `frontend/index.html`, `frontend/proof.html`, `frontend/lab.html` and
  `frontend/smarthome.html` are authored HTML entrypoints.
- `frontend/app.mjs`, `frontend/core/`, `frontend/features/` and `frontend/ui/`
  implement progressive enhancement, localization, live stats and contact.
- `frontend/styles/index.css` imports the independent UI v2 system in
  `frontend/styles/v2/` (tokens, base, layout, components, feature styles,
  responsive and print).
- `content/profile.json`, `content/translations/*.json` and the other
  `content/` UI sources contain approved CV facts and EN/DE/LV wording.
- `vite.config.mjs`, `scripts/build-frontend.mjs` and
  `scripts/localize-frontend.mjs` control the deterministic build.

`html/` is committed *generated output*, not authored source. It contains
`html/assets/`, `html/i18n/`, localized `/en/`, `/de/`, `/lv/` pages and the
localized `proof/` and `lab/` routes. `frontend-dist-manifest.json` records
asset entries and localized-page identities. Vite emits 12-hex-character
content-hashed asset names; the localized identity manifest records full
SHA-256 checksums. The homepage app entry additionally receives a
`?cfg=...` key derived from the first 12 SHA-256 hex digits of
`nginx.conf`. Do not hand-edit generated hashes.

## Public functionality and privacy

The core CV remains readable without JavaScript. JS enhances navigation,
language behavior, stats and phone/WhatsApp contact verification.
`frontend/features/contact.mjs` lazily loads Cloudflare Turnstile and calls
`/api/contact-config` and `/api/contact-reveal`; disclosure requires
server-side verification.

The public CV Assistant is **deferred**. Its launcher, dialog and chat
lazy import are not part of the public frontend. SIMPLE-DEPLOY Nginx
rejects `/api/chat`, `/api/chat-config` and `/api/chat-admission` with 404
while continuing to proxy contact and health endpoints. The contact/health-only
public Python entrypoint does not initialize Assistant SQLite for passive
startup or health GET requests. See
`docs/ui-v2/SIMPLE_FIRST_ASSISTANT_DEFERRED.md` and
`docs/SIMPLE_FIRST_SQLITE_STARTUP_BOUNDARY.md`.

Live stats use validated snapshots: malformed/non-finite and implausibly
future data are treated as offline, while snapshots older than 15 minutes
are marked cached/stale.

## Security, accessibility and caching

The active SIMPLE-DEPLOY `deploy/simple-deploy/nginx.conf` uses first-party
scripts, a per-request CSP nonce, reviewed Cloudflare Insights/Turnstile
script sources, `script-src-attr 'none'` and `style-src 'self'`. Do not
introduce `unsafe-inline`, `unsafe-eval` or unreviewed external scripts.
Hashed assets receive one-year immutable caching; HTML and `stats.json`
do not. The root `nginx.conf` is for the separate legacy two-container path.

Preserve heading order, keyboard navigation, focus return,
`:focus-visible`, reduced motion, accessible mobile-menu state and
Turnstile/contact status. Responsive validation includes 390, 430, 768,
1280 and 1440 CSS px. The retired Assistant modal contract is not a
currently reachable public feature.

## Validation

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build:frontend
npm run check:frontend
```

CI checks deterministic frontend rebuild, generated-artifact identity,
Python privacy/content contracts, Node behavior, Chromium/browser
accessibility, Nginx contracts, PDFs and security gates. Source changes
require matching committed `html/` and `frontend-dist-manifest.json` output;
documentation-only changes do not. For dated installed RPi5 evidence,
consult canonical GitHub handoff issue #347.

