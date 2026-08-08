# C6 accessibility audit

Gate C6 tracks issue #84 and PR #85. The production prerequisite is C5 main SHA `a044e4c612f4952e0d59a8b2b76779137f92d06e`, with successful main CI `31262571170` and trusted RPi5 deploy `31262622437`.

## Dialog decision

The existing custom chat modal remains authoritative for C6. It already provides the behaviors the current dialog guidance requires for this interface: focus is moved into the modal, keyboard focus is contained, Escape dismisses it, the background is made inert while open, and focus returns to the launcher after close. Replacing this working contract with native `<dialog>` would change several behaviors at once without a demonstrated accessibility improvement, so C6 does not perform that migration.

The decision is based on the current HTML/dialog guidance and the WAI-ARIA modal dialog pattern. Native `<dialog>` may be reconsidered later as a separate bounded change if it can be shown to be equal or better in the repository's real Chromium and assistive-technology-oriented regression tests.

References:
- https://html.spec.whatwg.org/multipage/interactive-elements.html#the-dialog-element
- https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/

## C6 product changes

- Language switchers are named `role="group"` controls while preserving the existing EN/DE/LV toggle-button `aria-pressed` state.
- Language buttons expose explicit accessible names: English, Deutsch and Latviešu.
- Successful contact verification transfers focus to the first newly revealed contact link after the Turnstile mount is hidden, avoiding focus loss for keyboard users.
- Smart Home device-card headings move from `h2` to `h3`, preserving the existing visual CSS while keeping Climate and Devices as the section-level `h2` headings.
- Chat streaming continues to keep the streamed answer itself out of live announcements while the concise status node reports progress/completion.

## Regression evidence

The bounded GitHub-hosted C6 finalizer validated the product transformation before publishing product commit `a01c743bc068bb01e3759ab9a9408cf520059c14`.

Run `31263772251` established:
- C6 source transform PASS;
- pinned Vite `8.1.5` double build byte-for-byte deterministic PASS;
- frontend dist contract PASS;
- frontend unit tests 12/12 PASS;
- HTML semantic tests 7/7 PASS;
- real Chromium keyboard/contact/language/Smart Home behavior PASS (`BROWSER_BEHAVIOR_SMOKE=PASS`, `C6_BROWSER_SEMANTICS=PASS`);
- source validation and secret scan PASS.

That run failed only after all product gates, during temporary finalizer self-clean because Git refused to remove a helper modified inside the runner without `-f`. The follow-up self-clean corrected only that publication mechanic and produced `a01c743bc068bb01e3759ab9a9408cf520059c14`; all temporary finalizer workflows/helpers are absent from the final PR diff.

## Preserved contracts

C6 does not change the chat/contact API payload contracts, C5 interaction-only dynamic imports, hidden-tab stats lifecycle, Turnstile interaction-only loading, CSP, deterministic Vite build, immutable hashed-asset model, RPi5 deployment ownership, or Cloudflare Tunnel ownership.
