# Public-repository readiness

Status: **BLOCKED**.

Do not change this repository from private to public until all gates below pass.

## Blocking gates

- [ ] Remove personal contact values from tracked source/tests if they are intended to remain protected by the Turnstile reveal flow.
- [ ] Decide how to handle historical commits that contain those contact values. A visibility change exposes reachable Git history; sanitizing only the current tree is not sufficient.
- [ ] Remove or redesign any `pull_request` workflow that can execute on the `rozkalns-cv-release` self-hosted runner. Public fork PRs must never execute untrusted code on the RPi5.
- [ ] Keep production deploy restricted to successful trusted `main` CI / explicit owner-controlled dispatch.
- [ ] Confirm full-history Gitleaks remains green with zero unresolved findings.
- [ ] Confirm Actions artifacts/logs and PR history are acceptable to expose publicly.
- [ ] Re-check branch/ruleset protection immediately after any visibility change.

## Current observations

- Main CI already performs a full Git-history Gitleaks scan with project-specific credential rules and detector canaries.
- The normal production deploy workflow is not PR-triggered; it resolves successful `main` CI and then deploys on the dedicated RPi5 runner.
- The current contact implementation/tests still contain full contact values as source/test literals even though the rendered page hides them behind Turnstile.
- The open Gate C0 audit branch currently contains `pull_request` workflows targeting the `rozkalns-cv-release` self-hosted runner. That branch must not coexist with a public visibility switch in its current form.

Do not change repository visibility until every blocking gate above is complete.
