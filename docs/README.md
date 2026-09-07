# Documentation index

This index separates **current source-level guidance** from dated engineering evidence.
GitHub remains canonical for mutable source, branch, issue, PR, CI and review state.
Repository documentation describes reviewed source contracts and intended architecture; it
does not by itself prove current production/runtime state, deployment state or the
active work queue. Revalidate those separately from fresh evidence when they matter.

Repository operating authority starts in [`../AGENTS.md`](../AGENTS.md), which points to
the active FAST-LANE contract below.

## Current / authoritative source contracts

These documents are the current repository-level starting points. “Current” here means
current **source documentation**, not a production receipt.

- [`FAST_LANE_V2_2.md`](FAST_LANE_V2_2.md) — active repository work-cycle contract.
- [`PROJECT_KNOWLEDGE.md`](PROJECT_KNOWLEDGE.md) — consolidated application ownership,
  architecture and source/deployment-boundary documentation.

## Architecture / operations

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — concise architecture and trust-boundary view.
- [`BUILD_DEPLOY_RUNBOOK.md`](BUILD_DEPLOY_RUNBOOK.md) — source-level build, release and
  deploy contract; production execution remains separately gated.
- [`FRONTEND.md`](FRONTEND.md) — frontend source/build organization.
- [`CONTENT_AUTHORING.md`](CONTENT_AUTHORING.md) — canonical content and localization
  authoring rules.
- [`ACCESSIBILITY_TESTING.md`](ACCESSIBILITY_TESTING.md) — accessibility validation
  contract.
- [`LIVE_STATS.md`](LIVE_STATS.md) — live-stats source/interface documentation.
- [`live-stats-scheduler.md`](live-stats-scheduler.md) — scheduler source contract.

## Security / privacy / assistant operations

- [`SUPPLY_CHAIN.md`](SUPPLY_CHAIN.md) — dependency, image and supply-chain controls.
- [`CV_ASSISTANT_PRIVACY.md`](CV_ASSISTANT_PRIVACY.md) — assistant privacy boundary.
- [`CVBOT_CHAT_ADMISSION.md`](CVBOT_CHAT_ADMISSION.md) — chat admission controls.
- [`CVBOT_CLIENT_SECRET.md`](CVBOT_CLIENT_SECRET.md) — client-secret handling contract.
- [`CVBOT_DATA_RETENTION.md`](CVBOT_DATA_RETENTION.md) — retention behavior and policy.
- [`CVBOT_HEALTH.md`](CVBOT_HEALTH.md) — assistant health/readiness contract.
- [`CVBOT_PROVIDER_STREAM.md`](CVBOT_PROVIDER_STREAM.md) — provider streaming contract.

## Engineering evidence / case studies

These documents are useful proof of engineering work but are not current runtime truth.

- [`TROUBLESHOOTING_CASE_STUDY.md`](TROUBLESHOOTING_CASE_STUDY.md) — public,
  evidence-backed troubleshooting/release case study.

## Historical audits / evidence

The following files preserve dated audits, migration records, baselines and acceptance
receipts. Keep their dates, SHA references and conclusions as historical provenance.
They must not be used to determine current `main`, current production/runtime state,
deploy status or the current work queue.

- [`A11Y_C6_AUDIT.md`](A11Y_C6_AUDIT.md)
- [`BRANCH_HYGIENE_AUDIT.md`](BRANCH_HYGIENE_AUDIT.md)
- [`C7_STATIC_AUDIT.md`](C7_STATIC_AUDIT.md)
- [`C8_DELIVERY_AUDIT.md`](C8_DELIVERY_AUDIT.md)
- [`C9_FINAL_ACCEPTANCE.md`](C9_FINAL_ACCEPTANCE.md)
- [`CSS_C4_AUDIT.md`](CSS_C4_AUDIT.md)
- [`FAST_LANE_V2_1.md`](FAST_LANE_V2_1.md) — compatibility filename only; v2.2 is active.
- [`MIGRATION_RUNBOOK.md`](MIGRATION_RUNBOOK.md)
- [`PUBLIC_READINESS.md`](PUBLIC_READINESS.md)
- [`RESEARCH_PROVENANCE.md`](RESEARCH_PROVENANCE.md)
- [`ui-v2/README.md`](ui-v2/README.md) — dated UI-v2 implementation baseline.

## Classification contract

`tests/test_current_operational_docs.py` requires every Markdown document under `docs/`
(other than this index) to appear in exactly one of the classifications above. Adding a
new document therefore requires an explicit decision about whether it is current
source guidance, operational/security documentation, engineering evidence or historical
evidence. The same test prevents historical entries from entering the current-authority
section and verifies the root README points visitors to this index and the high-value
current source docs.
