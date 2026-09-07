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

<!-- BEGIN GITHUB-ONLY-LIVE-ALL-V1-MANAGED -->
## GITHUB-ONLY / LIVE-ALL v1

Canonical shared contract: `rozkalnsandris/ops-workflows/docs/GITHUB_ONLY_LIVE_ALL.md` with machine invariants in `policy/github-only-live-all-v1.json`.

- `GITHUB-ONLY` (including `git hub only`) means fresh GitHub state, safe source/content/test work, and rollout preparation up to but not including the first live mutation.
- Persist deferred rollout state as public-safe `[DEPLOY-QUEUE]` issues in `rozkalnsandris/ops-workflows`; chat or memory is never the queue.
- Merge remains separately explicit. Neither `GITHUB-ONLY` nor `LIVE-ALL` authorizes merge.
- A GitHub write whose deterministic side effect changes production counts as live work and must not run under `GITHUB-ONLY`.
- Queue `READY` requires the final exact deployable SHA, exact target/entrypoint/preflight/verification/allowed mutations, and no outstanding separate prerequisite owner gate.
- `LIVE-ALL` snapshots only open `READY` items present at command start, freshly revalidates exact SHA/target/baseline and may execute only ordinary predeclared rollout mutations allowed by this repository.
- Cloudflare mutation, production secrets/credentials, host/runtime mutation beyond the exact reviewed rollout, production data writes, permission expansion and other separately gated authority remain excluded unless separately explicitly authorized.
- After any selected live mutation starts, error/ambiguity requires public-safe evidence preservation and STOP of the remaining batch; no automatic retry/rollback/cleanup/alternate mutation path unless explicitly pre-authorized.
- Existing security, deploy-validation and release rules remain authoritative and stricter where applicable.
<!-- END GITHUB-ONLY-LIVE-ALL-V1-MANAGED -->

## Security and deployment

Preserve the existing gitleaks, CodeQL, CI hardening and deploy-validation contracts. Do not weaken security/release checks merely to make FAST cheaper. Keep credentials out of Git, logs, fixtures and generated artifacts.

<!-- BEGIN START-GITHUB-ONLY-V1-MANAGED -->
## START_GITHUB_ONLY_V1 deterministic bootstrap amendment

Startup contract: `rozkalnsandris/ops-workflows/docs/START_GITHUB_ONLY_V1.md`.
Repository manifest: `.github/start-github-only.json`.

- `START <repository> GITHUB-ONLY` refreshes local rules/handoff, the pinned shared policy and START contract, current default branch/governance capability, active PRs, active issues/dependencies, and relevant deploy-queue items before selecting the manifest-defined canonical lane.
- Revalidate mutable GitHub state immediately before every state-dependent write.
- The absence of an open issue alone is NOT a STOP condition. Do not invent speculative work.
- If declared tie-breakers cannot resolve equally authoritative lanes, report `AMBIGUOUS_CANONICAL_LANE` instead of choosing arbitrarily.
- Final routing is one of `READY_FOR_MERGE`, `PARKED`, `STOP_ERROR`, `NEW_SCOPE_OR_RISK`, `AMBIGUOUS_CANONICAL_LANE`, or `IDLE`.
- `PARKED` is session-only. **EXECUTOR** availability is session capability, not **READY** rollout eligibility.
- Executor unavailability alone must not change `READY` to `BLOCKED`; use `BLOCKED` only for rollout eligibility or contract failure.
- Repository-local stricter safety and trust-boundary rules remain authoritative.
<!-- END START-GITHUB-ONLY-V1-MANAGED -->

<!-- BEGIN AGENT-WORK-CYCLE-V1-MANAGED -->
## Agent Work Cycle v1

Shared governance contract: `rozkalnsandris/ops-workflows/docs/AGENT_WORK_CYCLE_V1.md` with machine invariants in `policy/agent-work-cycle-v1.json`. Repository-local rules remain authoritative and may be stricter.

### Canonical state and minimum-sufficient retrieval

- GitHub is canonical for mutable source, branch, SHA, issue/PR, CI/review and authorization-continuity state. Never reuse mutable state from chat history without a fresh read.
- `START rozkalns-cv` uses the repository-local startup routing. Bootstrap only enough state to identify one current work item/lane/gate: current `AGENTS.md`/rules, canonical handoff or continuation when present, current default-branch SHA, and only the issue/PR state required by that lane.
- For a current PR, inspect only the current exact head, required checks, reviews and unresolved threads unless a failure or conflict requires deeper evidence.
- `SYNC rozkalns-cv` is incremental refresh of the current lane, not a repo-wide audit. Re-read a handoff only when continuation may have changed or is ambiguous.
- `turpini` resumes the same scope with incremental retrieval. It never creates MERGE, LIVE, retry, rollback, cleanup, credential, permission or runtime authority.
- Do not enumerate unrelated work or historical CI/log/comment/review history during normal START/SYNC. Broaden retrieval only demand-driven or under an explicit repository-local audit mode such as `AUDIT-HANDOFF`.

### Work execution and owner gates

- Prefer the smallest coherent fix and carry safe source/docs/tests/policy work through Draft PR, exact-head CI/review convergence and Ready when repository-local rules permit it.
- Technical intermediate steps such as CI polling, exact-head/diff checks, read-only preflight, evidence refresh and scope-preserving correction are not owner gates.
- MERGE remains an explicit owner decision unless a repository-local explicitly activated FULL mode already grants issue-scoped merge authority. Merge never implies LIVE/deploy authority.
- LIVE/deploy/runtime/credential/permission/production-data mutations require the separate exact authorization defined by repository-local rules.
- Authorization is consumed at the first authorized mutation. After mutation begins, any error, timeout, drift, ambiguity or authorization uncertainty is fail-closed: collect only necessary read-only evidence and STOP. No retry, rollback, cleanup or alternate mutation without fresh explicit authority unless it was pre-authorized.

### Terminal response — exact next command

Every user-visible work-cycle response that ends or pauses repository work must finish with exactly one copy-pasteable command as the final actionable content.

- Use `ACTION REQUIRED` only for a genuine owner authorization/decision gate; never manufacture a gate merely to satisfy this presentation rule.
- When a real owner gate exists, output the exact authorization command with current issue/PR identifiers and exact SHA/target bindings where applicable.
- When no owner gate exists and mutable GitHub/external state must be refreshed, output `SYNC rozkalns-cv`.
- When no owner gate exists and same-scope safe technical continuation is immediately available, output `turpini`.
- When the current outcome is complete and no same-scope continuation remains, output `START rozkalns-cv`.
- Give exactly one recommended command, not a menu. The response-format contract never grants authority by itself.
<!-- END AGENT-WORK-CYCLE-V1-MANAGED -->

## Repository-local source-only FULL mode

Machine contract: `.github/source-only-full.json`.

- Source-only FULL is **off by default**. Issue creation, issue text, labels, `START`, `SYNC`, `turpini`, FAST-LANE, GITHUB-ONLY and LIVE-ALL do not activate it.
- The only activation form is an explicit owner command for one open issue: `AUTO-RUN FULL rozkalns-cv #<issue>`.
- Activation freezes the issue scope, default branch, current base SHA and policy revision before the first mutation. Any scope expansion or unsafe drift fails closed.
- While active, FULL may perform only the finite source-delivery mutation classes listed in `.github/source-only-full.json`, including branch/source/docs/tests/generated-artifact work, Draft PR, bounded scope-preserving corrections, Ready transition and exact-head squash merge when every machine merge condition is satisfied.
- A FULL merge must bind the exact PR head SHA, revalidate the current head/base/policy state, require exact-head CI, require zero unresolved review threads and require no actionable review state.
- Source-only FULL does not grant LIVE authority. It never authorizes production deploy/pull-deploy activation, host/runtime/container mutation, Cloudflare/DNS/account changes, OpenAI account/billing/API-key changes, secrets/tokens, permissions/repository settings, production/application data writes, rollback or cutover.
- The public-repository privacy boundary remains unchanged: private job-search/vacancy/company context, residential or street address, protected phone data, credentials and other non-public personal context must not be copied into public source/issues merely because it exists in chat, Notion or another private source.
- After any authorized mutation begins, tool error, timeout, unexpected failure, authorization ambiguity, privacy uncertainty, branch/head drift or merge-condition mismatch requires read-only evidence preservation and STOP. No automatic retry, rollback, cleanup or alternate mutation path is implied by FULL.
- When FULL is not actively and validly bound to the current issue, the existing normal FAST-LANE rule applies: MERGE requires separate explicit owner authorization. FULL never implies deploy/LIVE authorization after merge.
