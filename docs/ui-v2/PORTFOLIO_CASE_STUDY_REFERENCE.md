# Portfolio case-study visual reference

Issue: #492

Reference base: `main=645717e63596a6ece415d9f4ef69367b9e6ecafc`

Status: **design reference only — not public CV factual source**

## Purpose

Preserve the recruiter-first portfolio direction agreed in the October 2026 design discussion so a later implementation can reproduce the same hierarchy without relying on chat history.

The intended direction is an **engineering portfolio inside the existing CV**, not a generic gallery and not a replacement for the recruiter-first CV structure.

Core principle:

> Screenshot / visual evidence → problem → action → proof → stack → status → case study / GitHub.

The portfolio should show evidence of practical Linux/support/operations work rather than only listing technologies.

## Critical factual and privacy boundary

The generated visual mockups are directional only.

They contain illustrative or invented details such as example dates, host names, hardware models, metric values, service state, project duration, generated portrait imagery and example infrastructure labels.

**None of those illustrative values become CV facts by appearing in a mockup.**

A later implementation must:

- use only evidence-backed facts from canonical repository/content sources;
- keep paid employment clearly separate from personal/lab engineering work;
- label incomplete work honestly, for example `In progress`;
- use privacy-safe screenshots or redacted/static demonstrations;
- never expose credentials, tokens, private IPs/hostnames, protected contact data, residential data or private job-search context;
- never imply production state solely from repository source;
- keep GitHub as deeper evidence, while the web page itself remains understandable without opening a repository.

## Generated visual references

The original generated PNGs were produced in the design session and remain local conversation artifacts. The active GitHub connector does not provide a safe direct binary upload path from that local runtime, so this document records deterministic provenance and the implementation contract instead of pretending the PNG bytes are present in the repository.

### A — desktop homepage concept

- dimensions: `1122 × 1402`
- local generated filename: `a_clean_modern_portfolio_website_landing_page_scr_1.png`
- SHA-256: `fbb5be638cc53684664bcd32a8bc6711ebb05998ed978338fc035823daf89327`

Visual intent:

- compact header;
- clear role/identity hero;
- primary CTAs for CV, GitHub and engineering proof;
- large `Featured Projects` block directly after the hero;
- three strong project cards rather than many small projects;
- screenshot/evidence preview at the top of every card;
- visible status badge;
- concise summary;
- short `Problem / Action / Proof` structure;
- technology tags;
- separate `View case study` and `GitHub` actions;
- skills and live homelab remain visible below but secondary to the featured work.

### B — Linux Operations Lab case-study concept

- dimensions: `1122 × 1402`
- local generated filename: `a_clean_modern_web_page_ui_screenshot_desktop_2_batch_1.png`
- SHA-256: `4ff1898c45fe30ae9ff93f22ec1711ec8a53036c12bcdf34f6632d601e78e3fb`

Visual intent:

- project title and honest status at the top;
- primary GitHub link;
- one large evidence screenshot;
- compact project metadata panel;
- dedicated sections:
  - `Problem`
  - `What I built`
  - `How I troubleshoot`
  - `Architecture / Lab overview`
  - `Proof`
  - `What I learned`
  - `Current limitations`
  - `Related evidence`
- troubleshooting/process evidence should be as important as the final result;
- limitations are presented positively and honestly instead of hiding incomplete work.

### C — mobile homepage concept

- dimensions: `941 × 1672`
- local generated filename: `a_clean_centered_product_portfolio_mobile_ui_mock_3_batch_2.png`
- SHA-256: `21ae0ca92ff1257914c22ab58cc87d915c4835ac609047c44f979e5df79f0ae4`

Visual intent:

- real mobile composition rather than desktop compressed to one column;
- compact identity header;
- short hero;
- immediately visible CTAs;
- stacked project cards;
- screenshot, status, title, summary, tags and actions remain visible without excessive scrolling inside one card;
- condensed skills and live-homelab proof after projects.

## Homepage information hierarchy

Target order:

1. Identity / targeted role / concise value proposition.
2. CV / GitHub / engineering-proof actions.
3. Featured Projects.
4. Skills.
5. Paid experience.
6. Live homelab / engineering evidence.
7. Education / languages / secondary content.
8. Privacy/contact/footer as required by the existing site contract.

The exact current factual ordering may be adjusted during implementation based on recruiter usability tests, but projects should appear early enough that a recruiter does not need to search for technical evidence.

## Featured-project card contract

Each flagship card should answer these questions quickly:

1. **What is it?**
2. **What problem did it address?**
3. **What did Andris actually do?**
4. **What evidence exists?**
5. **What technologies were used?**
6. **Is it complete, active or still in progress?**
7. **Where can a technical reviewer inspect deeper evidence?**

Recommended card anatomy:

```text
[ privacy-safe screenshot / evidence ]
[ status ]

Project title
1–2 sentence factual summary

Problem  ...
Action   ...
Proof    ...

[ Linux ] [ Bash ] [ systemd ] [...]

View case study →                  GitHub ↗
```

Do not turn cards into long README files. The homepage is the recruiter scan surface; detailed evidence belongs in the case study.

## Flagship project direction

The concept uses three flagship categories because three strong cases are easier to scan than a long undifferentiated repository list.

Candidate direction based on the current site structure:

- Linux Operations Lab;
- self-hosted Linux / operations environment;
- rozkalns.net CV platform.

These names are a design/navigation direction only. Final titles and copy must be derived from current canonical project facts at implementation time.

Other repositories can remain under a secondary `More projects` / GitHub surface until they have a strong evidence-backed case study.

## Case-study content contract

A case study should not read like marketing copy.

Recommended sections:

### Problem

What practical need, learning objective or operational problem existed?

### What I built / Action

What was actually configured, implemented or documented?

### How I troubleshoot

Show the reasoning loop where relevant:

`symptom → evidence → hypothesis → controlled test → verification → documentation/escalation`

### Architecture / workflow

Use a small diagram only when it helps a reviewer understand system boundaries.

Do not publish internal/private infrastructure details merely to make the diagram look more technical.

### Proof

Use verifiable evidence such as:

- privacy-safe terminal output;
- a monitoring/dashboard screenshot;
- test/CI evidence;
- runbooks or incident notes;
- a safe architecture diagram;
- source links;
- a live public result where genuinely applicable.

### What I learned

Use concrete, non-inflated learning outcomes.

### Current limitations

Incomplete projects may be public. State limitations accurately instead of inventing completeness.

### Related evidence

Link to focused repository files, runbooks, issues, demos or tests when useful.

## Screenshot policy

Screenshots are evidence, not decoration.

Good candidates:

- terminal troubleshooting evidence;
- service health/status output;
- monitoring dashboard;
- GitHub Actions/test result;
- application UI;
- architecture diagram;
- incident/recovery evidence.

Before publication, every screenshot must be reviewed for:

- secrets/tokens;
- private IPs or hostnames;
- private usernames/paths where unnecessary;
- private contact or account data;
- customer/employer/private job-search data;
- browser tabs/history;
- identifiers that unnecessarily expand the public attack surface.

When real screenshots are not safe, use a clearly labelled static/redacted demonstration rather than fabricated operational claims.

## Visual system direction

Preserve the existing UI-v2 identity where practical:

- warm/light page background;
- white or very-light card surfaces;
- deep navy primary text;
- restrained cobalt/blue accent;
- green only for genuine healthy/live state;
- amber/orange suitable for `In progress`;
- subtle borders and shadows;
- generous whitespace;
- rounded cards;
- strong readable typography;
- obvious keyboard focus;
- no decorative animation that delays recruiter scanning.

The mockup is a hierarchy/layout reference, not a mandate to copy every generated pixel.

## Desktop behavior

At wide widths:

- Featured Projects may use a three-card row when copy remains readable;
- cards should share a coherent visual height without hiding important content;
- screenshot aspect ratios should remain consistent;
- project metadata and actions must not require hover to discover;
- case-study pages may use a main evidence column plus a compact metadata sidebar.

## Mobile behavior

At mobile widths:

- one project card per row;
- image/evidence remains large enough to understand;
- CTAs remain touch-friendly;
- status never depends on color alone;
- tags wrap;
- no horizontal scrolling;
- case-study sections become a single reading column;
- diagrams must scale or simplify rather than become illegible.

## Implementation relationship to existing site

This reference does **not** authorize a framework rewrite.

Prefer evolving the current semantic/static frontend and existing deterministic build architecture.

The implementation should preserve:

- EN/DE/LV behavior and factual equivalence;
- PDF/CV access;
- accessibility contracts;
- no-JavaScript recruiter path;
- live stats semantics;
- CV Assistant/privacy boundaries;
- deterministic generated frontend artifacts;
- existing CI/security gates.

## Implementation acceptance direction

A later implementation is successful when:

- a recruiter can identify 2–3 strongest technical projects within the first meaningful page scan;
- each project shows evidence, not only technology labels;
- incomplete work is visibly honest;
- deeper GitHub evidence is optional rather than required for basic understanding;
- mobile remains usable and compact;
- screenshots are privacy-reviewed;
- factual CV content remains canonical and unchanged unless separately evidence-backed;
- exact-head validation and accessibility/browser checks remain green.

## Scope status

This document preserves the concept only.

It does not implement the redesign, change current public CV copy, add new project claims, publish the generated portrait, deploy anything, or authorize merge/LIVE work.
