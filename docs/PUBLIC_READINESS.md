# Public-repository readiness

Status: **PUBLIC — hardening complete**.

> **Historical evidence snapshot.** This file preserves the completed public-readiness review and its exact acceptance baseline. Do not use the `Final baseline` section to determine current `main`, production SHA, deploy status, or active work queue. For current operational architecture, use `docs/PROJECT_KNOWLEDGE.md`. For exact live source/production/work-queue continuity, use canonical issue #347 and its latest title/comments.

This document records the completed public-repository hardening posture for `rozkalns-cv`. The repository remains public and is expected to stay within the controls below. A future regression in any of these controls reopens readiness review; completion does not authorize weakening them.

## Completed public-readiness gates

- [x] #94 — current tracked/generated/PDF contact policy is remediated and guarded. The recruiting contact channel intentionally designated public remains public; protected phone semantics remain runtime-only and are not printed in public PDFs.
- [x] #88 — historical protected phone/address exposure has an explicit owner disposition: accept the documented history-only risk and preserve repository history. No Git-history rewrite or force-push is planned for that accepted historical exposure.
- [x] #89 — retained Actions artifacts/logs and historical PR/issue content were audited and dispositioned. No confirmed reusable credential value or protected current contact value was found in reviewed accessible evidence; accepted historical host-path/topology disclosure remains documented low-risk operational metadata.
- [x] #91 — effective `main` control-plane protection is configured and proven: PR-only change path, squash-only linear history, conversation resolution, deletion/non-fast-forward protection, and strict required GitHub Actions `validate`.
- [x] #156 — GitHub-native public security-analysis baseline was reviewed/remediated while retaining the repository's independent Gitleaks and Trivy gates.
- [x] #157 / PR #158 — public HTTP validation failures no longer serialize exception-object text across the public trust boundary.
- [x] #90 — the persistent public-repository RPi5 self-hosted release runner was replaced and retired. The RPi5-local pull controller passed a genuine AUTO-safe one-shot canary and recurring timer-driven execution proof; the recurring timer is enabled/active; the repository runner count was verified as zero; the legacy runner service and sudo reachability were removed.
- [x] PR #161 — the obsolete `.github/workflows/deploy-main.yml` self-hosted deployment workflow was removed, and source/tests now reject its reintroduction while preserving the public-response contract on the active pull-deploy path.
- [x] #92 — final live branch hygiene completed after #90. The approved batch deleted exactly 92 obsolete non-main refs through normal branch deletion, with no force-push/history rewrite; immediate final verification showed `main` as the only branch and zero open PRs.

## Security and CI invariants to preserve

- Ordinary pull-request CI executes only on GitHub-hosted runners; untrusted pull-request code must not execute on RPi5.
- The repository has no configured self-hosted Actions runner for CV release work.
- `main` changes require the protected PR path and the exact PR-head `validate` check before merge.
- CI retains complete-history Gitleaks scanning, deterministic frontend rebuild/verification, frontend behavior tests, real Chromium smoke, pinned nginx/HTTP response contracts, CVBot image identity checks, Trivy HIGH/CRITICAL scanning, and final clean-source revalidation.
- Production application deployment remains exact-main/CI gated, transactional and rollback-aware.
- The RPi5-local recurring pull controller remains least-privilege/fail-closed and must continue to distinguish AUTO-safe application changes from manual/control-plane/DB-host changes.
- Shared Cloudflare Tunnel ownership remains outside the CV repository; CV must not regain ownership of the shared connector lifecycle.
- Protected contact values, runtime secrets, Turnstile secrets/tokens, cookies and environment values must never be copied into tracked/public evidence.
- Branch deletion, history rewrite, production mutation, GitHub settings changes and RPi5 host/root mutations remain separate authorization boundaries.

## Historical contact-data disposition

The sanitized historical audit found protected phone/address ancestry broadly reachable through prior public Git history. The current tracked tree is guarded against reintroducing those protected semantics, but rewriting historical ancestry would change descendant commit identities, disrupt PR/reference integrity and still would not guarantee removal from old clones, forks or GitHub-managed caches/refs.

Owner disposition recorded 2026-08-11: **accept the residual history-only exposure and preserve repository history**. Do not perform a history rewrite or force-push for this accepted issue. Continue preventing protected phone/address values from re-entering the current tracked tree.

The recruiting contact channel explicitly designated public under the final #94 policy is not treated as protected historical contact data.

## Retained public-evidence disposition

The #89 audit enumerated retained Actions artifact metadata and reviewed representative accessible artifact families with bounded content inspection. Reviewed evidence did not establish a reusable credential value or protected current personal-contact value. Expired evidence is recorded as unavailable rather than falsely treated as scanned.

Historical issue/PR/job-log material can contain machine identity, absolute paths, internal naming and other topology details. Owner disposition recorded 2026-08-11: **accept the reviewed host-path/topology disclosure as documented low-risk operational metadata**. Do not rewrite Git history for this reason. Any future discovery of an actual reusable credential requires rotation/revocation first and the credential value must not be reproduced in public evidence.

The legacy public self-hosted runner and its active workflow reachability have now been retired, so equivalent new self-hosted deployment logs are no longer generated by this repository.

## GitHub control-plane disposition

The #91 post-public control-plane audit was remediated without weakening CI or production boundaries.

- Repository ruleset `main-protection` is Active and targets the default branch.
- There are no intended bypass actors for normal repository work.
- Matching refs block deletion and non-fast-forward updates and require linear history.
- Changes to `main` require a pull request; review conversations must be resolved; repository merge policy is squash-only.
- GitHub Actions `validate` is the strict required status check for the protected merge path.
- Ordinary PR CI remains GitHub-hosted with explicit read-only repository permissions.
- Repository Actions default workflow permissions and external-fork approval policy were owner-verified in the GitHub UI where the linked integration could not read the corresponding settings endpoints.

## Deployment-control disposition

Phase 3 replaced the persistent public-repository self-hosted release runner with an RPi5-local polling/pull controller using short-lived scoped GitHub App read authentication.

Proven sequence:

1. exact-main CI and deploy-impact classification gate;
2. genuine AUTO-safe one-shot controller canary PASS;
3. recurring timer activation and timer-driven controller execution PASS;
4. readiness remained `CURRENT` and the public application contract remained healthy;
5. legacy `rpi5-rozkalns-cv-release` runner deregistered;
6. legacy runner systemd service removed;
7. legacy runner sudo reachability removed;
8. repository self-hosted runner count verified as zero;
9. obsolete self-hosted deploy workflow removed from source by PR #161.

The recurring controller does not turn manual/control-plane changes into unattended production deployments. Existing classification and authorization boundaries remain authoritative.

## Branch-hygiene disposition

#92 regenerated the live inventory only after #90 completed, required a separate explicit owner authorization for deletion, and rechecked exact `main`, exact-main CI, all live refs, open PR heads and protection state immediately before mutation.

The approved cleanup removed exactly 92 classified obsolete non-main refs through normal GitHub ref deletion. No ref was force-moved, no history was rewritten and `main` was unchanged. Immediate final verification showed one branch total (`main`) and zero open PRs.

Future active PR branches are normal temporary workflow state; completed/superseded branches should not be allowed to accumulate again.

## Final baseline

At the start of this final readiness declaration:

- protected base `main`: `0d2c4f97708e509968358e56525fc0df864173d7`;
- exact-main CI #655 / run `31643356454`: **PASS** across all required validation/security/browser/runtime gates;
- last proven production application SHA: `edea046966b8e69c14fb652b799297b9ae1df1bf`;
- the `edea046...` → `0d2c4f...` delta is control-plane/source-cleanup only from PR #161 and does not require an application production deploy;
- #90: completed;
- #92: completed;
- repository self-hosted runner count: 0;
- obsolete non-main branch inventory: pruned.

This final readiness update is documentation-only. `PRODUCTION_DEPLOY_REQUIRED=no`.
