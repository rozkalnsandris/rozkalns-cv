# CV UI v2 — approved redesign baseline

Issue: #243

Baseline main SHA: `e0bc6dcfc2624d813eb2f5e786d0c30f6aad2ae8`

Baseline CI: GitHub Actions CI #786 / run `31853467602` = `success`.

## Purpose

This document turns the approved desktop/mobile mockup into an implementation contract for `rozkalns-cv`.

The visual mockup is directional for layout, hierarchy, spacing, typography and overall visual language. Generated portrait details, placeholder dates, placeholder job titles and placeholder metric values are **not** source of truth. The current repository content and live APIs remain authoritative for factual CV data.

## Approved visual direction

- warm off-white page background
- white / very-light card surfaces
- deep navy primary typography
- cobalt-blue accent
- green reserved for healthy/live state
- large editorial serif display type for the name and selected headings
- clean system sans-serif for body/UI text
- subtle borders and shadows
- rounded cards with generous whitespace
- asymmetric desktop hero
- true mobile-first composition rather than a squeezed desktop layout

## Recruiter-first information hierarchy

1. Identity / hero
2. Selected engineering projects
3. Skills
4. Experience
5. Live homelab evidence
6. Education / learning
7. Footer / secondary contact detail

The current live homelab remains an important proof point, but it must no longer delay access to the candidate's technical projects and core skills.

## Factual content rules

### Identity

Use the current CV source of truth:

- Andris Rožkalns
- DevOps / Linux Engineer wording must stay aligned with the current CV content and owner-approved positioning
- Dortmund, Germany
- Latvian: native
- English: fluent
- German: B1

### Paid employment

Do not invent professional DevOps employment to match the generated mockup.

Current chronology to preserve:

- Warehouse Employee — Sonepar Deutschland · Dortmund — Jul 2023 onward/current source-of-truth end state
- Painting Area Manager — SIA Koksne · Latvia — May 2020 – Jun 2023
- Warehouse / Shop Manager — SIA Apavu Bode · Latvia — Aug 2011 – Apr 2020
- Early IT / self-taught background — secondary school period, where useful

Personal engineering work must be visually strong but clearly distinguishable from paid employment.

### Selected engineering projects

Initial approved set:

1. Production Linux server stack
2. Hermes self-hosted AI agent
3. Monitoring & observability
4. Home automation

Project copy must use real technologies already present in the CV/repository and should be evidence-oriented rather than generic marketing text.

### Skills

Retain the current honest proficiency model. Visual regrouping is allowed, but skill level must not be inflated for design reasons.

Current model:

- Core
- Working knowledge
- Learning
- Foundations, if still useful after layout review

### Live homelab

Only live/real values may be shown as metrics. Generated mockup numbers are examples only.

The existing `/api/stats`-driven data remains authoritative for metrics already exposed by the site. New claims such as backup status require a real source before being presented as live truth.

## Desktop target

### Header

Compact horizontal header with:

- AR monogram / identity
- About
- Experience
- Projects
- Homelab
- Skills
- Contact
- language switcher integrated without dominating the page

### Hero

Three-part editorial composition:

- identity, summary, location and CTAs
- portrait
- one concise engineering/value card plus one evidence/key-facts card

The first viewport should answer:

- who is this?
- what role is targeted?
- where is he based?
- what has he actually built?
- how can I contact/download the CV?

### Main content

Use card/grid composition for projects and skills, followed by an accurate experience timeline and compact live-homelab proof card.

## Mobile target

Mobile is a separate layout decision, not a desktop shrink.

Required behavior:

- compact top bar
- identity/portrait card
- readable summary
- primary CTA buttons with large touch areas
- projects visible immediately after hero
- compact homelab proof
- secondary sections stacked with generous spacing
- navigation must not consume the first viewport
- no horizontal page scrolling

Target primary touch areas: approximately 48 CSS px where practical, with adequate separation between adjacent controls.

## Technical architecture

Do not migrate frameworks solely for this redesign.

Keep:

- semantic static HTML as the primary content source
- CSS Grid / Flexbox / media queries
- native JavaScript ES modules
- progressive enhancement
- existing live stats, contact verification, language switching and CV assistant boundaries
- deterministic Vite build contract

Important repository constraint: `frontend/` is authoritative source, while generated `html/` assets and `frontend-dist-manifest.json` are committed and CI verifies deterministic rebuild identity. Any frontend-source PR must therefore include its matching generated dist changes.

## Semantic HTML requirements

- one primary `h1`
- logical heading hierarchy
- `header`, `nav`, `main`, `section`, `article`, `aside`, `footer` where semantically appropriate
- meaningful DOM reading order
- real links/buttons for actions
- machine-readable `<time datetime="…">` where dates can be expressed accurately
- core CV text remains visible without JavaScript
- do not duplicate separate desktop/mobile content trees

## CSS implementation strategy

The final redesign should remain modular around the current split:

- `frontend/styles/tokens.css`
- `frontend/styles/base.css`
- `frontend/styles/layout.css`
- `frontend/styles/components.css`
- `frontend/styles/features/*`
- `frontend/styles/responsive.css`
- `frontend/styles/print.css`

Target direction:

- mobile-first base rules
- intrinsic sizing (`minmax`, `clamp`, wrapping)
- progressive larger-screen layouts
- no device-specific fixed-width hacks
- readable body/UI sizes
- visible `:focus-visible`
- `prefers-reduced-motion` preserved

## JavaScript rules

- keep `<script type="module">`
- do not add JS for layout work CSS can perform
- preserve progressive enhancement
- preserve current contact verification/Turnstile state contract
- preserve live stats failure/loading semantics
- preserve CV assistant dialog semantics/security boundaries

## Structured-data target

A later focused slice should migrate the current JSON-LD from standalone `Person` to:

- `ProfilePage`
- `mainEntity` → `Person`

Visible HTML and JSON-LD must agree. Do not add facts that only exist in a generated mockup.

## Planned implementation slices

### Slice A — baseline / source-of-truth

- persist approved design contract
- record exact pre-redesign baseline
- inventory build/CI coupling and factual constraints

### Slice B — semantic shell + visual system

- restructure HTML reading order
- introduce new design tokens
- new header/hero foundation
- rebuild deterministic frontend dist

### Slice C — recruiter content

- projects
- skills
- experience
- responsive mobile composition

### Slice D — live features

- homelab presentation
- contact reveal adaptation
- language switcher adaptation
- CV assistant/mobile adaptation

### Slice E — metadata / machine-readable polish

- `ProfilePage` JSON-LD
- metadata/theme-color review
- multilingual URL/hreflang decision or follow-up issue

## Validation matrix

Before any slice becomes Ready for review:

- exact-head CI must pass
- deterministic frontend rebuild must be clean
- Chromium smoke must pass
- keyboard/focus behavior reviewed
- representative widths reviewed: ~390, ~430, ~768, 1280, 1440+
- no invented CV facts
- no production deploy without separate owner authorization

## Closeout status — 2026-08-15

The implementation slices are now represented by merged UI v2 work for the visual shell, recruiter-first hierarchy, hero, projects/skills/experience, live-homelab evidence and ProfilePage/metadata polish.

The multilingual URL migration is deliberately tracked separately in #251. The current EN/DE/LV client-side language switch remains supported in #243; crawlable `/en/`, `/de/`, `/lv/` variants and reciprocal `hreflang` belong to that dedicated routing/SEO change.

The real-Chromium validation matrix is enforced at 390, 430, 768, 1280 and 1440 CSS px. Each width must keep the document/page shell free of horizontal overflow, keep the localized location row contained and retain at least 48 CSS px height for the primary language/action/contact/chat controls.

## Workflow boundary

`fresh main → fresh branch → focused change → commit → push → Draft PR → exact-head CI/manual review → Ready → STOP → explicit owner squash merge → exact-main CI → deploy classification`

Merge and production deploy remain separately owner-gated.
