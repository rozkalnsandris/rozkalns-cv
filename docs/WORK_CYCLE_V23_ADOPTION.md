# FAST-LANE v2.3 work-cycle adoption

This repository adopts the shared FAST-LANE v2.3 work-cycle contract from `rozkalnsandris/ops-workflows@274d58f2d9d3cb86feded2751b8f9009a4501f6b` under rollout issue `#124`.

## Bootstrap and START

`.github/agent-bootstrap.json` is routing metadata only. `AGENTS.md` remains authoritative and wins whenever local rules are stricter. START resolves one current lane with minimum-sufficient GitHub reads; safe same-scope work continues automatically through source/CI/Ready where local rules allow it.

Mutable SHA, PR, CI, review, runtime, deployment and one-time authorization state must never be persisted in the bootstrap manifest.

## Write preflight

`WRITE_PREFLIGHT_COMPACT_V1` is adopted through the existing `.github/github-api-access-v1.json` mechanism. No second local write-preflight framework is created. Branch, PR and durable-state collisions remain fail-closed/no-op according to the shared contract and local stricter rules.

## Source-only AUTO-RUN FULL

The existing `.github/source-only-full.json` remains the repository-local authority contract. FULL stays off by default and requires an exact owner command for one open issue.

For new explicit activations only, normalized state v2 is used with controller issue `#489`:

- target issue owns scope/run/revision/phase/branch/PR/correction/stop/gate/completion state;
- controller owns only the singleton lock and active run pointer;
- CI, reviews, unresolved threads and mergeability are always fresh GitHub facts;
- stale writers and transition collisions STOP;
- historical/legacy state is read-only and is not rewritten;
- the existing source-only merge authority is unchanged;
- FULL never grants LIVE/deploy/runtime/secrets/permissions/data authority.

Queue vNext `#96` is not activated.

## Deployment profile

The repository already uses SIMPLE-DEPLOY for deployable `main` source changes. This rollout does not change that model. `.github/workflows/simple-deploy.yml` ignores governance-only `.github/**`, `docs/**` and `tests/**` pushes so this work-cycle adoption itself does not trigger production deployment; any push containing deployable application/source paths continues to use the existing SIMPLE-DEPLOY flow.

## Rollout authority

This adoption is source/governance only. It does not authorize production deploy, host/runtime/container changes, Cloudflare/DNS/account changes, secrets/tokens, permissions/settings, production/application data writes, rollback/cutover, or Queue vNext activation.
