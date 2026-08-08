# Gate C8 — CSP, cache and origin/edge delivery audit

Baseline and production prerequisite: C7 merge `ddc63975931ba796ccbc4dd2c733cf21fde66dd7`.

C7 exact production proof:

- main CI: `31266047074`;
- serial RPi5 deploy: `31266098343`;
- deploy artifact: `rozkalns-cv-deploy-ddc63975931ba796ccbc4dd2c733cf21fde66dd7-run-31266098343`;
- deploy result: PASS, transaction committed, no rollback, shared ingress not controlled by this repository.

## Pinned Nginx origin matrix

C8 audit run `31266567308` reproduced the production Nginx image and current generated frontend locally.

Observed origin policy:

| Resource class | Origin behavior |
|---|---|
| `/` / HTML | `Cache-Control: no-cache` |
| hashed `.mjs` | `text/javascript`; `max-age=31536000` plus `public, max-age=31536000, immutable` |
| hashed CSS | `max-age=31536000` plus `public, max-age=31536000, immutable` |
| hashed i18n JSON | `max-age=31536000` plus `public, max-age=31536000, immutable` |
| hashed WebP | `image/webp`; `max-age=31536000` plus `public, max-age=31536000, immutable` |
| stable `/photo.jpg` | `max-age=3600` |
| stable PDFs | `max-age=3600` |

All representative responses retained `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, the restrictive permissions policy, and the nonce-based CSP. `script-src-attr 'none'` remains present and broad `unsafe-inline` / `unsafe-eval` remain absent from the application CSP.

The two Cache-Control fields on immutable assets are expected from the current configuration: Nginx `expires 1y` emits `Cache-Control: max-age=31536000`, while the explicit header adds `public, max-age=31536000, immutable`. They are compatible. C8 found no evidence that this representation causes Cloudflare cache ineligibility, so it is intentionally left unchanged.

## Actual Cloudflare edge evidence

The trusted RPi5 C7 post-deploy verifier observed the production hashed application module with:

- `Content-Type: text/javascript`;
- the one-year browser-cache fields including `immutable`;
- `X-Content-Type-Options: nosniff`;
- the expected CSP/security headers;
- `CF-Cache-Status: DYNAMIC`.

Cloudflare's current documented default cache behavior is extension-based rather than MIME-based. `.mjs` and `.json` are not in the default cacheable-extension list, while `.css`, `.webp` and `.pdf` are. Cloudflare documents `DYNAMIC` as a request that was not cache-eligible at request time. Therefore the application module's `DYNAMIC` status is not caused by the origin's immutable Cache-Control fields.

The GitHub-hosted C8 edge job was explicitly challenge-aware. Some paths were replaced by a Cloudflare bot challenge and are not treated as delivery evidence. The unchallenged representative paths were still useful:

- hashed CSS: HTTP 200, `CF-Cache-Status: MISS`, one-year `public, ... immutable` browser header;
- hashed WebP: HTTP 200, `CF-Cache-Status: MISS`, one-year `public, ... immutable` browser header;
- stable PDF: HTTP 200, `CF-Cache-Status: MISS`, browser `Cache-Control: max-age=14400`.

`MISS` proves those extension classes were edge-cache eligible in that Cloudflare location. The mixed challenge result is not used to infer root, i18n, photo or stats cache state.

## Browser TTL finding

The origin sends stable PDF assets with `max-age=3600`, but the observed Cloudflare edge response sends `max-age=14400` (four hours). Current Cloudflare documentation states that Browser Cache TTL can raise a lower origin `max-age`, and documents four hours as the default Browser Cache TTL. Selecting **Respect Existing Headers** prevents this browser-TTL override.

This is an external Cloudflare zone-setting behavior, not a regression introduced by the C2–C7 source/build migration and not a Cloudflare Tunnel ownership concern. No repository-side workaround is introduced: changing stable filenames, weakening cache headers, or restructuring Vite output merely to counter a zone-level browser TTL would be the wrong ownership boundary.

Recommended Cloudflare follow-up: set Browser Cache TTL to **Respect Existing Headers** if the intended one-hour freshness for stable JPEG/PDF URLs should be authoritative. Re-verify the stable PDF response after that zone-setting change.

## C8 decision

- No CSP change is justified.
- No Nginx cache-header rewrite is justified by the observed edge behavior.
- No `.mjs`/JSON filename or build-graph workaround is justified solely to enter Cloudflare's default extension cache; a narrowly scoped Cloudflare Cache Rule would be the correct layer if edge caching for content-hashed `.mjs`/i18n JSON is desired later.
- No Cloudflare Tunnel ownership/lifecycle change is required.
- No `cvbot`/API behavior changes are required.
- Repository `PRODUCTION_IMPACT=no` for C8: the gate is audit/documentation only.

## Documentation checked

- Nginx `ngx_http_headers_module` (`expires`, `add_header`, inheritance semantics).
- Cloudflare Default Cache Behavior and default cached file extensions.
- Cloudflare Origin Cache Control.
- Cloudflare cache response statuses (`DYNAMIC`, `MISS`, `HIT`, `BYPASS`).
- Cloudflare Browser Cache TTL / Edge and Browser TTL behavior.
- Cloudflare Cache Rules settings.

C8 is complete on the repository side once the temporary audit workflow is removed and the normal CI for the audit-only PR is green. The external Browser Cache TTL recommendation is deliberately recorded separately from the repository ownership boundary.
