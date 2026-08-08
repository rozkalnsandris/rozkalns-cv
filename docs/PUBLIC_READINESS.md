# Public-repository readiness

Status: **PUBLIC — remediation in progress**.

The repository is now public. Keep the remaining cleanup items below visible until they are resolved.

## Public-readiness gates

- [ ] #94 — dedicated recruiting email is intentionally public; phone remains runtime-protected; one-page public PDFs use a protected-site WhatsApp QR. Draft candidate build, focused regressions, source validation, and PDF/QR verification are complete; final merge/deploy evidence is pending.
- [ ] Decide how to handle historical commits that contain those contact values. Public visibility exposes reachable Git history; sanitizing only the current tree does not remove historical values.
- [x] Keep normal pull-request CI on GitHub-hosted runners. Current `main` does not contain a pull-request workflow targeting the `rozkalns-cv-release` self-hosted runner.
- [x] Keep production deploy restricted to successful trusted `main` CI / explicit owner-controlled dispatch.
- [x] Keep the full-history Gitleaks gate green with zero unresolved credential findings.
- [ ] Review Actions artifacts/logs and historical PR content for anything that should not remain public.
- [ ] Re-check branch/ruleset protection after the visibility change.

## Current observations

- Main CI performs a full Git-history Gitleaks scan with project-specific credential rules and detector canaries.
- The production deploy workflow is not PR-triggered; it resolves successful trusted `main` CI and deploys on the dedicated RPi5 runner.
- `andris@rozkalns.net` is intentionally public for recruiting. Phone values remain runtime configuration. Public PDFs use a QR to the verified-site WhatsApp flow instead of printing the phone number.
- The closed Gate C0 audit branch may remain reachable in public Git history even though its pull request is closed; it should not be treated as an active production workflow.

Historical contact cleanup, artifact review and post-visibility ruleset verification remain separate follow-up tasks.
