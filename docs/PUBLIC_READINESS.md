# Public-repository readiness

Status: **PUBLIC — remediation in progress**.

The repository is now public. Keep the remaining cleanup items below visible until they are resolved.

## Public-readiness gates

- [x] Remove personal contact values from the current tracked source/tests; the Turnstile reveal flow now reads contact values only from runtime environment variables.
- [ ] Decide how to handle historical commits that contain those contact values. Public visibility exposes reachable Git history; sanitizing only the current tree does not remove historical values.
- [x] Keep normal pull-request CI on GitHub-hosted runners. Current `main` does not contain a pull-request workflow targeting the `rozkalns-cv-release` self-hosted runner.
- [x] Keep production deploy restricted to successful trusted `main` CI / explicit owner-controlled dispatch.
- [x] Keep the full-history Gitleaks gate green with zero unresolved credential findings.
- [ ] Review Actions artifacts/logs and historical PR content for anything that should not remain public.
- [ ] Re-check branch/ruleset protection after the visibility change.

## Current observations

- Main CI performs a full Git-history Gitleaks scan with project-specific credential rules and detector canaries.
- The production deploy workflow is not PR-triggered; it resolves successful trusted `main` CI and deploys on the dedicated RPi5 runner.
- Contact values are runtime configuration; missing `CONTACT_*` values fail closed instead of falling back to embedded personal data.
- The closed Gate C0 audit branch may remain reachable in public Git history even though its pull request is closed; it should not be treated as an active production workflow.

Historical contact cleanup, artifact review and post-visibility ruleset verification remain separate follow-up tasks.
