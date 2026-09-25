# FAST-LANE v2.2 Composite — rozkalns-cv

This is the active local FAST-LANE startup contract. The older versioned filename is retained only for backward compatibility and is not startup authority.

## Core rule

**The human approves the RISK / DECISION. Automation executes the TECHNICAL STEPS.** Read-only checkpoints never create owner gates; STRICT describes live risk, not approval-per-command.

## FAST

`START`, `turpini`, or equivalent continuation may carry safe source work from fresh canonical GitHub state through Ready. Documentation/content, site/application source, tests and deterministic refactors may proceed in one batch, including branch, PR, CI/review and up to two scope-preserving corrections. Batch 2-5 related same-risk items when coherent. Merge remains explicit.

## Human gate budget and Composite STRICT

Normal delivery has at most two owner gates: **MERGE**, then **COMPOSITE LIVE** only when production/live mutation is required. Before the live gate, gather all read-only evidence. One bounded authorization binds exact SHA, exact target, allowed mutation categories, limits, exclusions and expected baseline; preflight and verification execute inside one fail-closed one-shot.

For deploy artifacts/versions, use pinned tooling, build once, verify the exact candidate, re-check production drift and deploy that exact verified artifact/version. Do not silently switch to newer `main`.

## Local STRICT boundaries

Production deploy/pull-deploy activation, Cloudflare production changes, credentials/secrets, host/runtime mutation, production data writes, permission expansion or another live authority change require Composite Live authorization.

## Failure and evidence

Authorization is consumed at first authorized mutation. Any later error/ambiguity requires evidence preservation and STOP; no automatic retry, rollback, cleanup or alternate mutation path unless explicitly pre-authorized.

Use one Ready receipt and one final live receipt. Put any remaining owner decision at the **end** under `ACTION REQUIRED`; when the owner must enter/run something, provide the exact copyable instruction in a fenced `bash` block.

Merge never authorizes deployment or another live mutation.

## GitHub API access v1

Repository consumer manifest: `.github/github-api-access-v1.json`, pinned to shared revision `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` in `rozkalnsandris/ops-workflows`.

- `START`, `SYNC`, `turpini` and PR continuation use serial, minimum-sufficient GitHub reads by default.
- Inspect changed files only when the current decision requires them; prefer current event/state evidence over historical run enumeration.
- Never tight-poll CI or reviews. Reuse same-step evidence when it remains sufficient, and refresh only when mutable state can have changed.
- Map rate-limit evidence to the shared deterministic read dispositions rather than broad retries or request fan-out.
- Before a merge or other authorized mutation, use the compact exact-head pre-mutation check defined by the shared contract.
- Never issue an automatic duplicate mutation after a `403`, `429`, timeout or transport ambiguity. Reconcile only with the minimum read-only evidence required, then STOP on an ambiguous outcome.
- This API-access contract does not create merge authority and does not create deploy, production, runtime, Cloudflare, secrets, permissions or production-data authority.
- Repository-local FAST, source-only FULL, privacy, security and deployment rules remain stricter and unchanged.
