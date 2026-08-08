# Gate C9 — production cutover and final acceptance

Date: 2026-08-08
Parent: #68
Child: #102

## Decision

C9 is an evidence-only final acceptance gate. No served frontend file, Nginx configuration, cvbot/API implementation, deployment workflow, RPi5 host infrastructure, dependency, or shared Cloudflare Tunnel lifecycle change is justified by this gate.

`PRODUCTION_IMPACT=no` for repository/runtime behavior.

The accepted production application revision is:

`4f14c8aa9a371f18e782afc2d23c662bce94a990`

## Exact production identity

The C8 documentation merge above completed the normal trusted release chain:

- `main` push CI: `31267349993` — PASS;
- serial RPi5 deploy: `31267391057` — PASS;
- evidence artifact: `rozkalns-cv-deploy-4f14c8aa9a371f18e782afc2d23c662bce94a990-run-31267391057`;
- artifact ID: `9024568753`;
- artifact digest: `sha256:cc5564d5ae4649c7ace09137953c6ae6304a6b94c2fe0b943d5f5f166d4c775d`.

RPi5 deploy evidence records:

- `TARGET_SHA=4f14c8aa9a371f18e782afc2d23c662bce94a990`;
- `FINAL_STATE_SHA=4f14c8aa9a371f18e782afc2d23c662bce94a990`;
- `DEPLOY_RESULT=PASS`;
- `TRANSACTION_COMMITTED=true`;
- `SHARED_INGRESS_CONTROLLED=false`;
- `DATABASE_MIGRATIONS_EXECUTED=false`;
- `ROLLBACK_PERFORMED=false` because the forward transaction succeeded.

The installed privileged deploy helper matched the exact reviewed source blob before deployment.

## Runtime health and production boundary

The post-deploy RPi5 artifact proves:

- `cv` is running and bound only to `127.0.0.1:8088`;
- `cvbot` runs the exact SHA-tagged image `rozkalns-cv-cvbot:4f14c8aa...` and is healthy;
- cvbot remains non-root (`10001:10001`), read-only-rootfs, all capabilities dropped, `no-new-privileges`, PID-limited, and only its data mount is writable;
- `LOCAL_URL=PASS` for `http://127.0.0.1:8088/`;
- `PUBLIC_URL=PASS` for `https://rozkalns.net/`;
- the repository did not control or reconcile the shared Cloudflare ingress.

The trusted public post-deploy verifier also passed:

- site response;
- hashed app module JavaScript MIME;
- immutable browser caching for the hashed app module;
- `X-Content-Type-Options: nosniff`;
- per-response nonce CSP;
- `script-src-attr 'none'`;
- no broad application `unsafe-inline` fallback.

The observed hashed `.mjs` edge status remains `CF-Cache-Status: DYNAMIC`, already explained and accepted in C8 as Cloudflare default extension eligibility rather than an origin cache-policy failure.

## Exact-source functional/browser proof

Exact production SHA `4f14c8aa...` passed main CI `31267349993`, including:

- source/Python behavioral coverage;
- deterministic Vite double-build and generated-dist drift gate;
- frontend source/unit behavior;
- real Chromium frontend smoke;
- full-history Gitleaks;
- pinned Nginx MIME/cache/CSP/security contracts;
- exact cvbot image identity;
- Trivy HIGH/CRITICAL vulnerability gate;
- clean-source revalidation after container checks.

The permanent Chromium smoke exercises the generated frontend with controlled API fixtures and proves the interaction contract without disclosing real production contact data or spending a real Turnstile token:

- English initial state and PDF mapping;
- Latvian switch, translated role, `/cv-lv.pdf`, and `aria-pressed` state;
- live/stale/invalid statistics behavior;
- chat open, focus trap, Escape close, focus return, streamed reply, completed-history bounds, and failure exclusion;
- Turnstile-gated contact reveal, token-only POST shape, successful reveal, and focus transfer to the newly revealed contact link;
- content-addressed WebP decode at 480×480 with reserved layout dimensions;
- Smart Home mobile landmarks, heading hierarchy, language controls, and device headings.

C9 additionally ran temporary GitHub-hosted browser proof `31267843383` against the same unchanged product tree. The workflow modified only the test workspace, not repository product source, to add an explicit German switch assertion before the existing Latvian switch. Real Chromium passed the full EN → DE → LV sequence, including German `/cv-de.pdf`, German role text, and language toggle state. The temporary workflow was removed after PASS.

This separation is intentional: production RPi5 evidence proves the exact deployed revision and real network/runtime health, while exact-source Chromium fixtures prove protected interaction semantics without bypassing Turnstile or logging/retrieving real contact data.

## Before/after evidence

### Public C0 baseline

C0 authoritative public baseline at `4135b9111308be4450c5d2fe801e322093c43f88` recorded:

- desktop cold transfer: `72,028 B`;
- desktop warm transfer: `1,968 B`;
- phone cold transfer: `71,516 B`;
- phone warm transfer: `1,963 B`;
- desktop Lighthouse performance `100`;
- phone Lighthouse performance `92` in the authoritative capture, with an earlier same-asset phone run scoring `73`, demonstrating synthetic mobile variance.

Later GitHub-hosted public measurements were sometimes replaced by Cloudflare challenges, so C9 does **not** manufacture a direct public-edge percentage from incompatible environments.

### Controlled frozen-SHA browser-work series

The comparable C5 controlled same-runner/Chrome series used frozen revisions and three-run medians:

- controlled C0 cold transfer: `97,801 B`;
- C4 cold transfer: `87,558 B` (`-10.47%` vs controlled C0);
- C5 cold transfer: `84,036 B` (`-4.02%` vs C4; `-14.07%` vs controlled C0);
- controlled C0 initial JS: `21,815 B`;
- C4 initial JS: `13,822 B` (`-36.6%`);
- C5 initial JS: `10,303 B` (`-25.46%` vs C4; `-52.77%` vs controlled C0);
- C5 cold request count stayed `8 → 8` versus C4;
- C5 warm transfer stayed `520 B`;
- chat/contact chunks are absent from the initial cold graph and load only on interaction;
- hidden tabs no longer perform recurring stats polling and refresh immediately when visible again.

### C7 image result

C7 independently reduced the initial profile-image payload without changing dimensions or the stable Open Graph JPEG:

- JPEG: `29,454 B`;
- selected WebP q85: `12,240 B`;
- saving: `17,214 B` (`-58.44%`).

This asset saving is reported independently rather than added to the controlled C5 total because C7 did not rerun the identical full browser-transfer methodology after Cloudflare challenge contamination was observed.

## Cache/security acceptance

C8 origin/edge evidence remains the accepted delivery contract:

- HTML and mutable runtime content are not immutable;
- content-addressed `.mjs`, CSS, i18n JSON and WebP receive long-lived immutable origin browser caching;
- stable JPEG/PDF resources remain stable-name resources;
- correct JavaScript MIME and `nosniff` remain enforced;
- nonce CSP, frame denial, referrer policy and permissions policy remain intact;
- shared Tunnel ownership remains outside this repository.

The one external zone-setting recommendation remains unchanged: Cloudflare was observed raising stable PDF browser `max-age` from origin `3600` to `14400`. If one-hour browser freshness must be authoritative, configure the Cloudflare zone Browser Cache TTL to **Respect Existing Headers** and re-check the PDF response. This is not a repository or Tunnel ownership change.

## Build/deployment model acceptance

The final architecture remains a static progressively enhanced site:

- Vite is build-only, never the production server;
- authoritative frontend source is human-readable;
- generated `html/` output is deterministic and CI-verified;
- hashed assets are produced from one build graph/manifest;
- HTML remains revalidated instead of immutable;
- chat/contact remain interaction-only dynamic chunks;
- stats remain first-render functionality but recurring background work pauses while hidden;
- the existing exact-SHA deploy transaction and automatic rollback path remain authoritative.

Official Vite production-build documentation was re-checked at C9: `vite build` produces static-hosting output and rewrites HTML/imported asset references as part of the build graph; it specifically recommends `Cache-Control: no-cache` for HTML when deployments rotate hashed assets. MDN HTTP caching guidance was also re-checked: content-addressed immutable subresources are an appropriate use of long `max-age` plus `immutable`. The repository's current build/cache architecture remains aligned with those documented semantics.

## Rollback acceptance

Rollback remains available and tested rather than exercised unnecessarily on a healthy deployment:

- deploy CI retains transactional fault-injection/rollback tests;
- the privileged helper backs up the managed runtime before mutation;
- a failed uncommitted mutation triggers rollback;
- rollback explicitly preserves the shared-ingress ownership boundary;
- current successful deployment committed forward and therefore correctly reports `ROLLBACK_PERFORMED=false`.

## C9 pre-merge verdict

PASS.

The real production revision is healthy and exact-SHA proven; the same product source passes deterministic build, browser, API-contract, security and supply-chain gates; controlled performance evidence shows less startup work; and no final production code/config correction is justified.

After this evidence-only PR is merged, close #102 and parent #68 only after the new documentation-only merge SHA completes the repository's normal `main` CI → serial RPi5 deployment proof. Because the PR changes documentation only, no served behavior change is expected.