# Repository operating rules

This repository contains the CV/site application, supporting automation and production/deploy integration. Git source delivery and live production authority are separate gates.

## FAST-LANE v2.1 Hybrid

Read `docs/FAST_LANE_V2_1.md` before implementation.

- **FAST** covers documentation/content, application source, tests and deterministic CI-safe changes through Ready when they do not deploy or expand a production trust boundary.
- FAST may batch **2-5 closely related same-risk work items** when they form one coherent acceptance story.
- After initial publication, at most **two scope-preserving corrective commits** may address CI/review findings; a third correction or material scope/risk expansion requires STOP.
- Use one Ready receipt and refresh mutable merge evidence immediately before merge.
- **STRICT** includes production deploy/pull-deploy activation, Cloudflare mutation, production secrets/credentials, host/runtime mutation, production data writes, permission expansion and equivalent live authority.
- Merge remains explicit owner authority and never authorizes deployment or another live mutation.

## Security and deployment

Preserve the existing gitleaks, CodeQL, CI hardening and deploy-validation contracts. Do not weaken security/release checks merely to make FAST cheaper. Keep credentials out of Git, logs, fixtures and generated artifacts.
