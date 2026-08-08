# Public-repository readiness

Status: **PUBLIC — remediation in progress**.

The repository is now public. Keep the remaining cleanup items below visible until they are resolved.

## Public-readiness gates

- [ ] Complete #94 current-tree contact remediation. The candidate source model removes tracked email/phone values from canonical content and generated assistant knowledge, but the legacy public PDFs still require an explicit owner privacy decision before this gate can close.
- [ ] Decide how to handle historical commits that contain protected contact/location data (#88). Public visibility exposes reachable Git history; sanitizing only the current tree does not remove historical values.
- [x] Keep normal pull-request CI on GitHub-hosted runners. Current `main` does not contain a pull-request workflow targeting the `rozkalns-cv-release` self-hosted runner.
- [x] Keep production deploy restricted to successful trusted `main` CI / explicit owner-controlled dispatch.
- [x] Keep the full-history Gitleaks gate green with zero unresolved credential findings.
- [ ] Review Actions artifacts/logs and historical PR content for anything that should not remain public (#89).
- [ ] Re-check branch/ruleset protection after the visibility change (#91).
- [ ] Replace the persistent public-repository release runner with the reviewed safer control plane (#90).
- [ ] Classify and prune stale non-main branches (#92).

## Current observations

- Main CI performs a full Git-history Gitleaks scan with project-specific credential rules and detector canaries.
- The production deploy workflow is not PR-triggered; it resolves successful trusted `main` CI and deploys on the dedicated RPi5 runner.
- `bot/contact.py` already loads the real contact channels only from runtime environment variables and fails closed when they are absent.
- Read-only #88/#94 audit found that current `main` still duplicated the protected email/phone values in canonical `content/profile.json` and generated assistant knowledge despite the Turnstile reveal design.
- #94 changes the canonical contract so email/phone are `verified-runtime` policy only and cannot carry tracked values.
- The existing committed PDF files are legacy public static artifacts. Until the owner explicitly chooses a PDF contact policy, `content/pdf-manifest.json` records `legacy-public-contact-pending-owner-decision` and deliberately does not bind those PDFs to the new canonical source digest.
- Historical audit also found that the initial imported assistant source contained more precise personal location data than the current public professional profile; #88 owns the history-only disposition and values must not be repeated in public evidence.
- The closed Gate C0 audit branch may remain reachable in public Git history even though its pull request is closed; it should not be treated as an active production workflow.

Current-source remediation (#94), historical personal-data handling (#88), retained evidence review (#89), post-public settings verification (#91), release-runner migration (#90), and branch cleanup (#92) remain separate gates.
