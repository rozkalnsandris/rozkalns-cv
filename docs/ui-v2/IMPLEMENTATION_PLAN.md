# UI v2 redesign implementation plan

Status: dedicated implementation workspace

Tracking model: **feature branch + Draft PR**, not an issue queue.

## Purpose

Implement the recruiter-first CV/portfolio UI redesign without mixing incomplete redesign work into `main`.

The redesign should stay inside the existing `rozkalns-cv` repository and preserve the current application architecture unless a later reviewed change proves a framework rewrite is necessary.

## Design reference

The visual direction is preserved separately in the current design-reference work under PR #493 and `docs/ui-v2/`.

The mockups are visual/layout references only. They are not factual sources for CV content, metrics, dates, infrastructure details or employment claims.

## Dependency and reference asset status

PR #493 is a separate sibling Draft PR based on `main`; it is **not** an ancestor of this branch.

Until that reference work is merged and this branch is updated from the resulting `main`, the implementation must treat PR #493 as the external design-reference dependency.

The three original PNG mockups are not currently stored in this branch or on `main`. Their filenames, dimensions and SHA-256 provenance are recorded in PR #493. Do not describe the PNG bytes as repository-preserved until they are actually committed.

Before the Codex visual-polish phase, prefer storing verified copies under:

`docs/ui-v2/references/`

and verify their SHA-256 values against the provenance recorded in PR #493. Use a safe binary upload path; do not reconstruct images from filenames, descriptions or hashes.


## Working branch

All redesign implementation work belongs on:

`ui/v2-redesign`

`main` remains the stable/canonical release line until the redesign is reviewed and explicitly merged.

## Delivery strategy

### Phase 1 — approximately 70–80% with screenshot-to-code tooling

Use Google Stitch or another suitable screenshot-to-code workflow to reproduce:

- desktop homepage;
- mobile homepage;
- Linux Operations Lab case-study page.

Prioritize:

1. semantic layout structure;
2. responsive behavior;
3. overall visual proportions;
4. typography hierarchy;
5. reusable project cards, badges, buttons and detail sections;
6. integration with the existing content model.

Do not spend time chasing 1–2 px differences in this phase.

### Phase 2 — integrate into the existing CV frontend

Adapt the generated prototype to the repository rather than replacing repository architecture blindly.

Preserve:

- Vite/static build model;
- EN / DE / LV behavior and factual equivalence;
- canonical content sources;
- PDF/CV access;
- no-JavaScript recruiter path;
- accessibility behavior;
- live stats semantics;
- CV Assistant/privacy boundaries;
- deterministic generated frontend artifacts;
- existing CI/security gates.

Avoid:

- framework migration only for cosmetic reasons;
- large duplicated markup;
- excessive absolute positioning;
- hard-coded mockup facts;
- unnecessary client-side JavaScript.

### Phase 3 — structural cleanup and verification

Before visual polishing:

- normalize HTML semantics;
- consolidate CSS variables and reusable classes;
- verify desktop and mobile breakpoints;
- remove generated-code duplication;
- check keyboard/focus behavior;
- run existing frontend/CI checks;
- verify privacy-safe screenshots and assets.

### Phase 4 — Codex polish when quota is available

Use Codex on the already-working implementation instead of rebuilding from scratch.

Codex task:

> Compare the current UI v2 implementation against the verified desktop/mobile/case-study reference mockups. Keep the existing architecture and functionality. Refactor generated markup/CSS where necessary, fix responsive differences, accessibility problems and visual inconsistencies, then iterate with browser screenshots until the implementation is close to the references.

Target after this phase: approximately **90–95% visual fidelity**, with maintainable source rather than screenshot-specific hacks.

### Phase 5 — release gate

The redesign is ready for owner review when:

- desktop and mobile layouts closely match the references;
- the strongest projects are visible early in the recruiter scan;
- case-study pages show problem → action → proof clearly;
- all published claims come from canonical evidence;
- EN / DE / LV remain coherent;
- no horizontal overflow or major layout shifts remain;
- accessibility/browser checks pass;
- deterministic frontend/build checks pass;
- no secrets/private infrastructure data appear in assets;
- the implementation PR is reviewable as one coherent UI change.

Merge and LIVE/deployment remain separate owner-authorized steps.

## Scope rule

Keep this branch focused on the UI v2 redesign. Unrelated CV content, infrastructure, runtime and deployment work should remain outside this branch unless directly required by the redesign and explicitly reviewed.
