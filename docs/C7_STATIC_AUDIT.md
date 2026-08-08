# Gate C7 — static payload and cache audit

Baseline: C6 production SHA `81a1cfcb63d53a7b05e1304907c1951495ca2d9b`.

## Inventory

- Profile JPEG: 29,454 bytes, 480×480, SHA-256 `f9a54c7dd9df18ed6938981b418d8a5d7b4068efc26962a9a489c4957f93e6aa`.
- HTML reserves the rendered profile image at 118×118.
- Favicon SVG: 369 bytes; no format optimization is justified.
- PDFs are stable download URLs and remain byte-identical: EN 117,269 B / `1234942691c7bd90502f43fabdf312267567cad0e5d0a09f9ab427e024364776`; DE 119,532 B / `3e03d46adc75b95c9359802f5e6b5d541a6a8bbcd663300dbc5f2657b1ff7b64`; LV 117,665 B / `a1677d8160f96516aa73595ca9959ad5d52f63f4363259fd29eb64091a6736b0`.

## Cache audit

Pinned Nginx origin run `31264671874` confirmed HTML uses `Cache-Control: no-cache`; stable photo/favicon/PDF URLs use a one-hour freshness lifetime; and content-hashed JS/CSS/i18n assets use one-year `immutable` caching. GitHub-hosted probes against the public Cloudflare edge were excluded because the edge returned a bot challenge; edge/origin policy is deferred to C8.

## Image candidate

Read-only run `31264744352` encoded the same 480×480 JPEG with libwebp/cwebp 1.3.2, `-preset photo -m 6`:

| Candidate | Bytes | Saving vs JPEG | All-PSNR |
|---|---:|---:|---:|
| WebP q80 | 9,474 | 67.83% | 44.19 dB |
| WebP q85 | 12,240 | 58.44% | 45.77 dB |
| WebP q90 | 17,576 | 40.33% | 47.96 dB |

q85 was selected after visual comparison against the committed JPEG: it preserves the 480×480 source dimensions and appearance while removing 17,214 bytes from the normal profile-image transfer. The original JPEG remains at `/photo.jpg` for the Open Graph URL; the rendered CV references `frontend/photo.webp`, which Vite emits as a content-hashed asset.

## Decision

- Add only the q85 WebP to the Vite asset graph.
- Keep the original JPEG for Open Graph compatibility and as the canonical stable social-image URL.
- Extend the existing immutable hashed-asset cache rule to WebP.
- Do not change PDFs, favicon, runtime endpoints, Cloudflare ownership, or the deploy model.
- Preserve explicit 118×118 image dimensions and all C6 accessibility behavior.

## Final implementation evidence

The verified product commit is `906f6001f81a85e6cfa4d2b4a467c39e62b473f5` (`perf: hash optimized profile image and cache it immutably`). The reproducible q85 source asset is 12,240 bytes with SHA-256 `1070aa250e2eaa0be5da0245f7815d7a93923f81f9780bac00b9d79aae79cf51`. Vite emits it as `assets/photo.18997b6089ce.webp` and records it under the `index.html` asset graph.

The finalizer passed the deterministic double build, frontend contract, semantic tests, real Chromium behavior smoke, pinned-Nginx WebP MIME/cache checks, stable Open Graph JPEG check, unchanged PDF hashes, and source hygiene before publishing the product commit. All temporary C7 audit/finalizer workflows and helper scripts were removed from the final PR diff.

`PRODUCTION_IMPACT=yes` because the served profile asset and Nginx cache matching change.
