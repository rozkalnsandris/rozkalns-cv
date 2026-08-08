# Gate C4 CSS source audit

## Frozen C3 baseline

C4 was based on merged and production-verified C3 SHA `88d20510e80b9dd7665cb19a24b14b3c9d30ee89`.

Pre-change authoritative CSS source:

- `frontend/styles/main.css`: 200 lines; Git blob `5a07da172cbb2b7ed606e4ca9e1f4215ff080987`.
- `frontend/styles/extra.css`: 58 lines; Git blob `0a40ed13f7baf2b0e8c7fd1a1ee33829f912ff29`.
- CV loaded `main.css` first and `extra.css` second.
- Smart Home loaded `main.css` only.

The C3 Vite manifest contained two production CSS assets:

- `assets/i18n.222474672f5a.css`
- `assets/app.c34d399843db.css`

## Selector overlap

The only intentional historical selector override between `main.css` and `extra.css` was `.skill-chip::before`:

- `main.css` supplied the legacy diamond marker.
- `extra.css` disabled that pseudo-element after SVG skill icons became authoritative.

C4 removes the pseudo-element rule completely and keeps `.skill-chip svg` in the shared component source. The remaining historical `extra.css` rules were contact-verification/action-icon feature rules plus their mobile and print conditions; they now live with their owning responsibilities instead of a later patch layer.

## Authoritative C4 ownership

- `tokens.css`: one visual token set for colors, typography, layout width/rhythm, spacing, radii and named breakpoint values.
- `base.css`: reset, document defaults, focus behavior and reduced motion.
- `layout.css`: page, sidebar and section layout.
- `components.css`: shared UI and CV content components.
- `features/stats.css`: live statistics.
- `features/chat.css`: assistant dialog.
- `features/contact.css`: Turnstile/contact reveal.
- `features/smarthome.css`: Smart Home demo.
- `responsive.css`: the single owner of max-width media-query rules.
- `print.css`: the single owner of print behavior.
- `index.css`: the single ordered stylesheet source entry consumed by both HTML entry points.

CSS custom properties are not portable media-query conditions, so the 760px, 560px and 620px conditions remain explicit in `responsive.css`; the source contract binds those values to `--breakpoint-layout`, `--breakpoint-compact` and `--breakpoint-contact` so they cannot drift independently. `main.css` and `extra.css` are retired and source validation rejects their return.

## Generated output

The final C4 Vite graph emits exactly one shared production CSS asset:

- `assets/i18n.6672c32ef8b9.css` (16,650 bytes)

The final refresh built the frontend twice with pinned Node 24.18.0 and Vite 8.1.5. The generated trees and manifests were byte-identical. `npm run check:frontend` passed with 7 manifest assets; JavaScript, CSS, translations and HTML all remained within their existing budgets. The focused frontend and Python source/dist contracts also passed before the generated output was committed.

No RPi5 pull-request execution and no Cloudflare Tunnel ownership/lifecycle change are part of C4.
