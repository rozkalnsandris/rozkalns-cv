# FAST-LANE v2.1 Hybrid — rozkalns-cv

## FAST

Documentation/content, site/application source, tests and deterministic refactors are FAST while they remain Git/CI-only. A FAST batch may include 2-5 related same-risk work items and up to two scope-preserving corrective commits after CI/review findings.

## STRICT

Separate explicit owner authorization is required for production deploy/pull-deploy activation, Cloudflare production changes, credentials/secrets, host/runtime mutation, production data writes, permission expansion or another live authority change.

## CI and evidence

The existing CI/CodeQL/deploy-hardening checks remain intact in Phase 1 because they are part of the production trust contract. FAST-LANE reduces PR/authorization/evidence repetition rather than bypassing release security.

Produce one Ready receipt with lane, related work, exact base/head, CI/reviews, reviewed scope, deploy/trust classification and next gate. Merge remains explicit owner authority and never authorizes deployment.
