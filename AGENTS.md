# Repository operating rules

This repository contains the CV/site application, supporting automation and production/deploy integration. Git source delivery and live production authority are separate gates.

<!-- BEGIN FAST-LANE-V2.2-MANAGED -->
## FAST-LANE v2.2 Composite

Read `docs/FAST_LANE_V2_2.md` as the active local startup contract.

**Primary rule:** the human approves the **RISK / DECISION**; automation executes the **TECHNICAL STEPS**.

- `START`, `turpini`, or equivalent continuation may carry safe documentation/content, application source, tests and deterministic CI-safe work through Ready when it does not deploy or expand a production trust boundary.
- FAST may batch **2-5 closely related same-risk work items** and use up to **two scope-preserving corrective commits** for CI/review findings.
- Normal delivery has at most two owner gates: explicit **MERGE**, then one bounded **COMPOSITE LIVE** only when production/live mutation is required.
- Read-only validation, evidence refresh, CI/review inspection, candidate verification and reconciliation are technical steps, not owner gates.
- Composite Live must bind exact SHA, exact target, allowed mutation categories, practical limits, explicit exclusions and expected baseline when relevant.
- Authorization is consumed at the first authorized mutation. Any later error, ambiguity or drift requires evidence preservation and STOP; no automatic retry, rollback, cleanup or alternate mutation path unless explicitly pre-authorized.
- **STRICT** includes production deploy/pull-deploy activation, Cloudflare mutation, production secrets/credentials, host/runtime mutation, production data writes, permission expansion and equivalent live authority.
- Put any remaining owner decision visibly at the end under `ACTION REQUIRED` and provide exact copyable input when needed.
- Merge remains explicit owner authority and never authorizes deployment or another live mutation.
<!-- END FAST-LANE-V2.2-MANAGED -->

## Security and deployment

Preserve the existing gitleaks, CodeQL, CI hardening and deploy-validation contracts. Do not weaken security/release checks merely to make FAST cheaper. Keep credentials out of Git, logs, fixtures and generated artifacts.
