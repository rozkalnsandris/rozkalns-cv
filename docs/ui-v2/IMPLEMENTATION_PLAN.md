# UI v2 implementation — 7 October 2026

Status: implementation complete; source and browser verification on `ui/v2-redesign`.

## Outcome and sequence

1. Reconcile the existing design/reference lane with current main. Preserve the original three mockups in `references/`; their SHA-256 values match `PORTFOLIO_CASE_STUDY_REFERENCE.md` exactly.
2. Build a compact header and portrait hero, followed immediately by three project cards. Use white/blue surfaces, sans-serif hierarchy and consistent evidence previews. Place skills and live homelab together, then background, experience, education and contact.
3. Provide a dedicated, localized Linux Operations Lab case study with problem, work, troubleshooting method, workflow, evidence and limitations. Link supporting projects to the existing engineering-proof page.
4. Keep semantic HTML in `frontend/*.html`, fresh CSS in `frontend/styles/v2/` and factual/localized copy in `content/`. Preserve Vite, EN/DE/LV, PDFs, no-JavaScript navigation, live-state semantics and contact/assistant privacy boundaries.
5. Verify deterministic builds, existing source contracts, browser/accessibility behavior and screenshots at desktop/mobile widths. Deliver one source PR. Merge and deployment remain separate owner gates.

## Candidate direction and factual boundary

The current Notion CV positioning and study plan were read on 7 October: Junior Technical Support / Linux Operations, with Application Support/NOC as adjacent targets. English is the public master. DevOps is a later growth direction. Existing canonical profile data already expresses this direction; do not inflate it for the redesign.

The public linux-operations-lab tree inspected on 7 October contains a roadmap and templates, not completed incident case reports. Present it as in progress and describe evidence targets as targets. Do not manufacture terminal output or claim completed exercises. Use clearly labelled repository/workflow previews, the existing real portrait and canonical Raspberry Pi 5 facts. Generated Proxmox hardware, service status, dates and uptime in mockups are illustrative only.

Public content must not include private job-search allocation, employer strategy, home address or protected phone data. No Notion study-workflow instructions are execution instructions for this UI task.

## Review checklist

- Projects directly follow the hero; three columns on wide screens, one on phones.
- Real HTML/CSS components; no screenshot used as a functioning interface.
- Lab detail has inspectable source links and honest limitations.
- All new reader-facing wording is available in EN/DE/LV.
- PDF, email, verified phone and assistant paths remain usable.
- Keyboard focus, mobile menu, no-JS navigation, reduced motion and offline status work.
- Existing build, privacy, browser and content checks pass.
- Screenshot comparison uses the attached original references; typography/proportions may adapt to truthful copy and the real portrait.

## Source map and preview

- `frontend/index.html`: homepage markup; `frontend/lab.html`: dedicated lab case study; `frontend/proof.html`: supporting technical evidence.
- `frontend/styles/v2/tokens.css`, `layout.css`, `components.css`, `responsive.css`: reusable design, layout and responsive rules. HTML contains no embedded styling.
- `content/profile.json` and existing translations: unchanged factual CV/PDF source.
- `content/ui-v2.json`: new EN/DE/LV homepage interface wording. `content/lab.json`: localized lab case-study copy, grounded in the public lab repository.
- `scripts/localize-frontend.mjs`: static language routes, case-study metadata and localized project links. The new lab is JavaScript-free.

Build with `npm ci --ignore-scripts --no-audit --no-fund` and `npm run build:frontend`. Serve the generated `html/` directory with a local HTTP server; open `/en/`, `/de/`, `/lv/` and the matching `/lab/` routes. Never serve the repository root publicly.

The UI v2 source contract allows up to 27,000 bytes of combined JavaScript (mobile navigation), 28,000 bytes of shared CSS (new project/case-study components), and 38,000 bytes per homepage (semantic project facts, summaries and vector icons). Lab HTML is capped at 10,000 bytes per locale. The existing 128 KiB initial-page budget and security/privacy gates remain unchanged.

## Owner refinement: independent v2 style system

The owner clarified that the entire v2 must follow the new references, with no legacy CSS or inherited visual components. All public entries now load only `frontend/styles/v2/` through the small style entrypoint. The former CSS modules have been removed. Contact verification, the assistant dialog, statistics, professional background, education, privacy and the supporting pages are restyled as part of the same v2 system. The assistant lives in the contact section instead of covering project content with a floating launcher. Functional IDs and data bindings are preserved for accessibility, language, content and privacy behavior; they do not import the old visual design.

## Verification receipt

Local verification: 482 Python tests and 35 Node tests pass; source validation, content/PDF consistency, secret/public-artifact privacy checks and deterministic frontend rebuild pass. Chromium smoke, EN/DE/LV case-study accessibility, no-JavaScript behavior, layout stability and runtime-error suites pass. Desktop and 390px screenshots were visually inspected; the mobile menu opens and closes using Escape. Initial localized pages remain below 128 KiB. Live service status is unavailable in a local preview, so no production health is inferred.
