# Public-repository readiness

Status: **PUBLIC — remediation in progress**.

The repository is public. Keep the remaining cleanup items below visible until they are resolved.

## Public-readiness gates

- [x] #94 — dedicated recruiting email is intentionally public; phone remains runtime-protected; one-page public PDFs use the protected-site WhatsApp flow. Current tracked/generated/PDF outputs are guarded against reintroducing the protected phone.
- [x] #88 — historical phone/address exposure is accepted as documented history-only risk. The current tracked tree is clean for protected phone/address semantics; no Git-history rewrite, force-push or ref rewrite is authorized or planned.
- [x] Keep normal pull-request CI on GitHub-hosted runners. Current `main` does not contain a pull-request workflow targeting the legacy `rozkalns-cv-release` self-hosted runner.
- [x] Keep production deploy restricted to successful trusted exact-`main` CI and explicit owner-controlled deployment boundaries.
- [x] Keep the full-history Gitleaks gate green with zero unresolved credential findings.
- [x] #89 — retained Actions artifacts/logs and historical PR/issue content were audited and dispositioned. No reusable credential value, protected personal contact value or RFC1918/LAN coordinate was found in the reviewed accessible surfaces; historical host-path/topology metadata is accepted as documented low-risk operational metadata, expired evidence is recorded as unavailable, and legacy self-hosted deploy log cleanup is deferred until #90 retires the runner/reachability.
- [ ] #91 — verify effective post-public `main` ruleset, merge policy, fork-workflow approval and least-privilege Actions settings.
- [ ] #90 — complete replacement of the persistent public-repository RPi5 release runner. The pull/controller baseline is installed and production/classifier state is reconciled; the remaining path waits for a genuine newer `AUTO_DEPLOY_SAFE` delta, one-shot controller canary, recurring replacement proof and separately authorized legacy-runner retirement.
- [ ] #92 — after #90 completes, regenerate the live branch inventory and prune only separately approved obsolete refs.

## Historical contact-data disposition

The sanitized historical audit found protected phone/address ancestry effectively repository-wide across the inspected public Git refs. The current tree is clean for the protected values, but rewriting the historical ancestry would change descendant commit identities, disrupt reference/PR integrity and require coordinated destructive ref updates while still not guaranteeing removal from old clones, forks or GitHub-managed cached/ref surfaces.

Owner disposition recorded 2026-08-11: **accept the residual history-only exposure and preserve repository history**. Continue preventing protected phone/address values from re-entering the current tracked tree. Do not perform a history rewrite or force-push for this issue.

The dedicated recruiting email remains intentionally public and is not treated as protected historical contact data under the final #94 policy.

## Retained public-evidence disposition

The #89 audit enumerated all 163 retained Actions artifact metadata records and reviewed representative active artifact families manifest-first with bounded content inspection. Reviewed accessible artifacts did not contain a confirmed reusable credential value, protected personal contact value, RFC1918/LAN address, raw secret environment dump or RPi5 user-home path. Older expired evidence is explicitly recorded as unavailable rather than treated as scanned.

Bounded legacy self-hosted deploy job-log samples consistently expose runner/machine identity, absolute runner-work/helper paths and internal deploy/container naming. Historical issue/PR text also contains absolute production/runtime paths; issue #44 identifies the location and filesystem ownership/mode of a root-only host credential file, but not the credential value itself.

Owner disposition recorded 2026-08-11: **accept the reviewed host-path/topology disclosure as documented low-risk operational metadata**. Do not delete benign active artifacts solely for normal CI/public evidence. Do not rewrite history or force-push refs for this issue. Defer one-time legacy self-hosted deploy job-log cleanup until #90 has retired the repository runner/reachability so equivalent public logs are not recreated immediately after cleanup. Any future discovery of an actual reusable credential value requires rotation/revocation first and must not be reproduced in public evidence.

## Current observations

- Main CI performs a full Git-history Gitleaks scan with project-specific credential rules and detector canaries.
- Production deploy remains exact-main/CI gated and transactional. The legacy self-hosted release path remains temporarily present while #90 finishes migration to the RPi5-local pull/controller execution path.
- The replacement controller/readiness baseline is installed with the recurring timer disabled/inactive. The last proven production/classifier baseline is `4a0069a97022841da07a687a197ea8cfacc56cd6`; current CV `main` is newer because of documentation-only public-readiness work and the full production-to-current-main range remains `NO_DEPLOY`.
- `andris@rozkalns.net` is intentionally public for recruiting. Phone values remain runtime configuration. Public PDFs use the verified-site WhatsApp flow instead of printing the phone number.
- Closed audit/migration branches may remain reachable in public Git history until #90 completes and #92 performs its final separately authorized live branch cleanup.

Remaining public-hardening work is tracked in #91, #90 and #92. No production deployment is required for this documentation-only update.
