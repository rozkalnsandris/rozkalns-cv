# Public branch hygiene audit v2 — issue #92

Generated from the live public-ref inventory on 2026-08-09 after the cvbot hardening series and #90 pull-deploy source work advanced.

- Audited base: current `main` after the #139 merge and the immediate no-op recovery of an accidental audit-placeholder write.
- Total branches after creating this audit branch: **80**.
- Non-main branches classified: **79**.
- Conservative delete candidates: **63**.
- Review-before-delete: **14**.
- Preserve now: **2**.

This is classification evidence only. **No branch deletion, force-move, history rewrite, production deploy, runner removal, sudoers/systemd mutation or Cloudflare change is authorized by this document.** Every delete candidate must be re-resolved against the live ref set and open PR set immediately before deletion.

## Classification policy

- `delete-candidate`: implementation is merged/completed or explicitly superseded by an authoritative replacement; no current active work is known to require the branch. This is not deletion authorization.
- `review-before-delete`: unique or audit/control-plane history exists and the replacement/archival decision should be confirmed before deletion.
- `preserve`: branch is part of current unresolved work or is this audit branch.

## Preserve now — 2

- `audit/88-history-rescope-v02` — #88 remains at the owner decision boundary for historical PII disposition.
- `audit/92-branch-hygiene-v02` — current audit branch.

## Review before deletion — 14

- `audit/94-production-proof-v01`
- `audit/101-final-production-proof-v01`
- `audit/119-production-proof-v01`
- `automation/m3-pull-deploy-preflight`
- `docs/readme-wide-banner-33`
- `fix/cloudflared-canonical-ready`
- `fix/cloudflared-ready-gate-41`
- `fix/supply-chain-hardening-v01`
- `fix/52-nginx-mjs-mime-clean`
- `fix/112-chat-retention`
- `fix/112-chat-retention-expiry`
- `fix/113-dedicated-client-secret`
- `security/remove-contact-literals-public-readiness`
- `security/94-current-contact-literals-v01`

These branches are intentionally excluded from the automatic candidate bucket because they contain unique audit/recovery/control-plane history or lack sufficient current replacement evidence in the connector-visible metadata.

## Conservative delete candidates — 63

- `a11y/84-semantic-interaction-v01`
- `audit/gate-c0-baseline-70`
- `audit/88-history-scope-v01`
- `audit/92-branch-hygiene-v01` — superseded by this v2 audit.
- `audit/96-csp-cache-origin-v01`
- `audit/102-production-final-proof-v01`
- `automation/m3-deploy-impact-classifier`
- `automation/m3-pull-deploy-preflight-v2`
- `chore/branding-cv-29`
- `chore/remove-legacy-source-writers-v01`
- `docs/final-ingress-boundary`
- `docs/issue-99-readme-modernize`
- `docs/readme-banner-raster-fix`
- `feat/58-turnstile-contact-icons`
- `fix/assistant-request-safety-v01`
- `fix/baseline-deploy-health-evidence-v01`
- `fix/cloudflared-edge-ready-canary`
- `fix/cloudflared-runtime-reconcile`
- `fix/cvbot-runtime-security-evidence`
- `fix/deploy-compose-env-static-permissions-v01`
- `fix/deterministic-live-stats-v01`
- `fix/pin-effective-compose-network-v01`
- `fix/supply-chain-hardening-v02`
- `fix/transactional-deploy-retention-v01`
- `fix/42-remove-cv-cloudflare-ownership`
- `fix/44-pin-compose-file`
- `fix/47-loopback-cv-origin`
- `fix/49-loopback-deploy-health`
- `fix/51-browser-smoke-link-state`
- `fix/52-nginx-mjs-mime`
- `fix/54-nginx-config-recreate`
- `fix/56-restore-rich-cv-layout`
- `fix/58-live-stats-contact-turnstile`
- `fix/58-live-stats-runtime-contract`
- `fix/62-live-stats-systemd`
- `fix/64-stats-shell-exec`
- `fix/66-prometheus-endpoint-discovery`
- `fix/77-portable-public-header-parse-v01`
- `fix/94-current-contact-privacy` — superseded by the final merged #94 contact model.
- `fix/94-public-email-verified-whatsapp-v2` — superseded by later #94 iterations.
- `fix/94-public-email-verified-whatsapp-v3` — superseded by merged #119.
- `fix/94-public-email-whatsapp-qr-v4` — merged via #119.
- `fix/111-deepseek-v4-contract`
- `fix/112-chat-retention-expiry-v2`
- `fix/113-dedicated-client-secret-v2`
- `fix/114-server-side-phone-output-policy`
- `fix/115-liveness-readiness`
- `fix/116-sse-stream-contract`
- `fix/117-chat-admission`
- `infra/90-helper-transport-decoupling` — merged via #138; activation remains separately gated by #90.
- `infra/90-pull-artifact-identity-gate` — merged via #139; activation remains separately gated by #90.
- `perf/82-reduce-initial-background-work-v01`
- `perf/86-static-payload-cache-v01`
- `rebuild/canonical-on-main-v01`
- `refactor/canonical-cv-content-v01`
- `refactor/frontend-accessibility-v01`
- `refactor/72-frontend-source-dist-v01`
- `refactor/75-unify-i18n-features-v01`
- `refactor/80-consolidate-css-v01`
- `refactor/118-app-factory-services` — merged via #136.
- `test/browser-behavior-ci-v01`
- `test/browser-behavior-ci-v02`
- `test/frontend-rpi5-readonly-v01`

## State changes since v1

The prior #128 snapshot saw 68 total branches / 67 non-main. It is now closed unmerged as stale. Since then the repository accumulated the #111–#118 cvbot branches plus the #90 automation/infra branches and the #88 rescope branch; several PRs that v1 treated as active are now merged, superseded or explicitly closed.

The temporary/superseded open PRs #95, #106 and #123 were closed without merge during this refresh. Their branches remain present and are classified above; no branch was deleted.

## Final deletion preflight required

Before any future deletion batch:

1. enumerate live branches again;
2. enumerate all open PR heads again;
3. compare every proposed candidate with current `main` and confirm merged ancestry or explicit replacement proof;
4. search current `main` for branch-name references in workflows, scripts and docs;
5. remove any branch that became active from the candidate set;
6. present the exact final names to the owner and obtain separate deletion authorization;
7. delete through normal GitHub branch deletion only — never force-move refs.

`PRODUCTION_DEPLOY_REQUIRED=no`: this audit changes documentation only and performs no runtime/control-plane activation.