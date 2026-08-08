# Public branch hygiene audit — issue #92

- Generated: `2026-08-08T18:49:41+00:00`
- Audited `main`: `0149bed2b84803f6fd8c191920191730c7a887cb`
- Total remote branches at audit time: **68**
- Non-main branches classified: **67**
- Delete candidates: **48**
- Preserve / active / explicit-review: **10**
- Additional review before deletion: **9**

The issue baseline of 47 non-main branches is stale; this audit intentionally uses the live remote-ref snapshot. Classification is read-only. **No branch deletion is authorized by this document.**

## Classification rules

- `active/open-PR`: at least one currently open PR uses the branch as its head; preserve.
- `merged/completed`: branch tip is already reachable from current `main`, or its latest PR is merged; candidate only when current `main` does not reference the branch by name.
- `closed/superseded`: latest PR is closed unmerged; automatic delete-candidate status requires explicit `superseded by #N` proof in that PR body and no current-main reference.
- `temporary/test`: audit/test/chore/release/docs branch without an open PR; unique history or references force manual review.
- `unique historical/recovery`: unique unmerged history without sufficient replacement proof; preserve pending explicit archive/delete decision.
- `elevated-public-review`: unique commits touch automation/runtime-sensitive paths such as `.github/`, `runner/`, `bot/`, `scripts/`, Compose or Nginx. This is a review flag, not evidence of a secret finding.

## Inventory

| Branch | Tip | Date | Age d | A/B | Main ancestor | PR | PR state | Replacement | Class | Decision | Risk | Main refs |
|---|---|---:|---:|---:|:---:|---:|---|---|---|---|---|---|
| `a11y/84-semantic-interaction-v01` | `84090e9a963d` | 2026-08-08 | 0 | 16/9 | no | #85 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `audit/101-final-production-proof-v01` | `ac69f5ab0957` | 2026-08-08 | 0 | 2/5 | no | #103 | closed | — | closed/superseded | **review-before-delete** | unique-history-review | — |
| `audit/102-production-final-proof-v01` | `ae0c28345709` | 2026-08-08 | 0 | 16/5 | no | #104 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `audit/119-production-proof-v01` | `69d1cd57ec83` | 2026-08-08 | 0 | 1/1 | no | #123 | open | — | active/open-PR | **preserve** | active | — |
| `audit/88-history-scope-v01` | `2ebb175b5058` | 2026-08-08 | 0 | 3/4 | no | #109 | closed | — | closed/superseded | **review-before-delete** | elevated-public-review | — |
| `audit/92-branch-hygiene-v01` | `28b9511fa15e` | 2026-08-08 | 0 | 1/0 | no | #128 | open | — | active/open-PR | **preserve** | active | — |
| `audit/94-production-proof-v01` | `f2c90bc3ac82` | 2026-08-08 | 0 | 1/4 | no | #107 | closed | — | closed/superseded | **review-before-delete** | elevated-public-review | — |
| `audit/96-csp-cache-origin-v01` | `4c5ec544f26f` | 2026-08-08 | 0 | 6/7 | no | #98 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `audit/gate-c0-baseline-70` | `57000f283f97` | 2026-08-08 | 0 | 0/13 | yes | #71 | closed | — | merged/completed | **delete-candidate** | low | — |
| `chore/branding-cv-29` | `25a9e9b1a680` | 2026-08-06 | 1 | 7/40 | no | #30 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `chore/remove-legacy-source-writers-v01` | `609821846256` | 2026-08-06 | 2 | 8/42 | no | #22 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `docs/final-ingress-boundary` | `214836e0a0fb` | 2026-08-07 | 1 | 1/29 | no | #46 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `docs/issue-99-readme-modernize` | `41a297e9af92` | 2026-08-08 | 0 | 1/7 | no | #100 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `docs/readme-banner-raster-fix` | `6ce011b193fd` | 2026-08-07 | 1 | 2/33 | no | #39 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `docs/readme-wide-banner-33` | `fe515ad19650` | 2026-08-07 | 1 | 2/35 | no | #34 | closed | — | closed/superseded | **review-before-delete** | unique-history-review | — |
| `feat/58-turnstile-contact-icons` | `ec9339b748e2` | 2026-08-07 | 0 | 15/22 | no | #60 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/111-deepseek-v4-contract` | `91058c85508a` | 2026-08-08 | 0 | 3/4 | no | #120 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/112-chat-retention` | `aabf1e47135c` | 2026-08-08 | 0 | 6/2 | no | — | — | — | unique historical/recovery | **preserve-review** | elevated-public-review | — |
| `fix/112-chat-retention-expiry` | `36d85fe9b29d` | 2026-08-08 | 0 | 9/2 | no | #122 | closed | — | closed/superseded | **review-before-delete** | elevated-public-review | — |
| `fix/112-chat-retention-expiry-v2` | `682a66a7db41` | 2026-08-08 | 0 | 3/1 | no | #124 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/113-dedicated-client-secret` | `449d9f5f21ba` | 2026-08-08 | 0 | 11/1 | no | #126 | closed | — | closed/superseded | **review-before-delete** | elevated-public-review | — |
| `fix/113-dedicated-client-secret-v2` | `808ac36300bf` | 2026-08-08 | 0 | 3/0 | no | #127 | open | — | active/open-PR | **preserve** | active | — |
| `fix/42-remove-cv-cloudflare-ownership` | `17048fcf563c` | 2026-08-07 | 1 | 13/31 | no | #43 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/44-pin-compose-file` | `d061e9efa314` | 2026-08-07 | 1 | 4/30 | no | #45 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/47-loopback-cv-origin` | `c46f01c5b7f4` | 2026-08-07 | 1 | 5/28 | no | #48 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/49-loopback-deploy-health` | `f19b4260005e` | 2026-08-07 | 1 | 2/27 | no | #50 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/51-browser-smoke-link-state` | `92c13a49cd1c` | 2026-08-08 | 0 | 1/17 | no | #69 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `fix/52-nginx-mjs-mime` | `2635c952fb05` | 2026-08-07 | 1 | 5/26 | no | #53 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/52-nginx-mjs-mime-clean` | `2635c952fb05` | 2026-08-07 | 1 | 5/26 | no | — | — | — | unique historical/recovery | **preserve-review** | elevated-public-review | — |
| `fix/54-nginx-config-recreate` | `89191a2b571d` | 2026-08-07 | 0 | 16/25 | no | #55 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/56-restore-rich-cv-layout` | `8d346674177b` | 2026-08-07 | 0 | 11/24 | no | #57 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `fix/58-live-stats-contact-turnstile` | `b09a785cad25` | 2026-08-07 | 0 | 2/23 | no | #59 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `fix/58-live-stats-runtime-contract` | `27f3610517f2` | 2026-08-07 | 0 | 2/22 | no | #61 | merged | — | merged/completed | **delete-candidate** | unique-history-review | — |
| `fix/62-live-stats-systemd` | `35e8fcc4a1c1` | 2026-08-07 | 0 | 5/20 | no | #63 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/64-stats-shell-exec` | `08271aa50fe8` | 2026-08-07 | 0 | 7/19 | no | #65 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/66-prometheus-endpoint-discovery` | `52ccbabb424d` | 2026-08-07 | 0 | 6/18 | no | #67 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/77-portable-public-header-parse-v01` | `44314f191d14` | 2026-08-08 | 0 | 2/13 | no | #78 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/94-current-contact-privacy` | `67879bcc8e77` | 2026-08-08 | 0 | 41/8 | no | #95 | open | — | active/open-PR | **preserve** | active | — |
| `fix/94-public-email-verified-whatsapp-v2` | `4a85a475d94e` | 2026-08-08 | 0 | 18/5 | no | #106 | open | — | active/open-PR | **preserve** | active | — |
| `fix/94-public-email-verified-whatsapp-v3` | `5d1e9dc09887` | 2026-08-08 | 0 | 18/4 | no | #108 | closed | — | closed/superseded | **review-before-delete** | elevated-public-review | — |
| `fix/94-public-email-whatsapp-qr-v4` | `0c0506912d01` | 2026-08-08 | 0 | 16/2 | no | #119 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/assistant-request-safety-v01` | `0112bccf6a0a` | 2026-08-06 | 2 | 13/43 | no | #21 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/baseline-deploy-health-evidence-v01` | `34c2efc7cf38` | 2026-08-06 | 2 | 2/47 | no | #2 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/cloudflared-canonical-ready` | `b3610b85865f` | 2026-08-07 | 1 | 1/32 | no | — | — | — | unique historical/recovery | **preserve-review** | unique-history-review | — |
| `fix/cloudflared-edge-ready-canary` | `fe7fbcc3bd94` | 2026-08-07 | 1 | 4/33 | no | #40 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/cloudflared-ready-gate-41` | `e38abfa00ed9` | 2026-08-07 | 1 | 1/31 | no | — | — | — | unique historical/recovery | **preserve-review** | unique-history-review | — |
| `fix/cloudflared-runtime-reconcile` | `ba70841235fe` | 2026-08-07 | 1 | 3/35 | no | #36 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/cvbot-runtime-security-evidence` | `874fb3076a7a` | 2026-08-07 | 1 | 3/34 | no | #37 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/deploy-compose-env-static-permissions-v01` | `e1185790820a` | 2026-08-06 | 2 | 2/46 | no | #4 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/deterministic-live-stats-v01` | `37661fab25ca` | 2026-08-06 | 2 | 6/42 | no | #23 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/pin-effective-compose-network-v01` | `82e503ed75bd` | 2026-08-06 | 2 | 6/44 | no | #20 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/supply-chain-hardening-v01` | `60628489670a` | 2026-08-07 | 1 | 31/41 | no | #24 | closed | — | closed/superseded | **review-before-delete** | elevated-public-review | — |
| `fix/supply-chain-hardening-v02` | `1dcbd75f0d44` | 2026-08-07 | 1 | 3/36 | no | #32 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `fix/transactional-deploy-retention-v01` | `706b53857c32` | 2026-08-06 | 2 | 4/45 | no | #19 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `perf/82-reduce-initial-background-work-v01` | `496cf35bb580` | 2026-08-08 | 0 | 28/10 | no | #83 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `perf/86-static-payload-cache-v01` | `f25b52781c19` | 2026-08-08 | 0 | 17/8 | no | #87 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `rebuild/canonical-on-main-v01` | `329ce1e2e6e7` | 2026-08-07 | 1 | 8/38 | no | — | — | — | unique historical/recovery | **preserve-review** | elevated-public-review | — |
| `refactor/72-frontend-source-dist-v01` | `0a46fab15e55` | 2026-08-08 | 0 | 40/15 | no | #73 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `refactor/75-unify-i18n-features-v01` | `4b49478b2429` | 2026-08-08 | 0 | 41/12 | no | #76 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `refactor/80-consolidate-css-v01` | `d7d8dad46990` | 2026-08-08 | 0 | 68/11 | no | #81 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `refactor/canonical-cv-content-v01` | `f6deefb091a4` | 2026-08-07 | 1 | 34/40 | no | #26 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `refactor/frontend-accessibility-v01` | `9b2ba2eee864` | 2026-08-07 | 1 | 18/40 | no | #25 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `security/94-current-contact-literals-v01` | `7680ade3765a` | 2026-08-08 | 0 | 16/5 | no | #105 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `security/remove-contact-literals-public-readiness` | `3af9cc93883e` | 2026-08-08 | 0 | 3/14 | no | #74 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `test/browser-behavior-ci-v01` | `e304715518f3` | 2026-08-07 | 1 | 27/40 | no | #27 | closed | — | closed/superseded | **review-before-delete** | elevated-public-review | — |
| `test/browser-behavior-ci-v02` | `a1eb45a5c202` | 2026-08-07 | 1 | 13/37 | no | #31 | merged | — | merged/completed | **delete-candidate** | elevated-public-review | — |
| `test/frontend-rpi5-readonly-v01` | `57000f283f97` | 2026-08-08 | 0 | 0/13 | yes | #28 | closed | — | merged/completed | **delete-candidate** | low | — |

## Owner-approval deletion candidate set

- [ ] `a11y/84-semantic-interaction-v01` — `84090e9a963d6b105fc699095a1306a2896a1a70` — merged/completed — PR #85 (merged)
- [ ] `audit/102-production-final-proof-v01` — `ae0c28345709c4d695c9b0c622429cd12f420ae6` — merged/completed — PR #104 (merged)
- [ ] `audit/96-csp-cache-origin-v01` — `4c5ec544f26fce54abc3f2f4463d59edc6490fd7` — merged/completed — PR #98 (merged)
- [ ] `audit/gate-c0-baseline-70` — `57000f283f97f1a06b6803c89aeaef82592a390e` — merged/completed — PR #71 (closed)
- [ ] `chore/branding-cv-29` — `25a9e9b1a680fe2747af4b85c4c3f142c213ca57` — merged/completed — PR #30 (merged)
- [ ] `chore/remove-legacy-source-writers-v01` — `609821846256dceb09881a5a1686118792599f7b` — merged/completed — PR #22 (merged)
- [ ] `docs/final-ingress-boundary` — `214836e0a0fbdc238f91cc7893ba5a83736899a0` — merged/completed — PR #46 (merged)
- [ ] `docs/issue-99-readme-modernize` — `41a297e9af9284c3e4066687f5ba54767217f83d` — merged/completed — PR #100 (merged)
- [ ] `docs/readme-banner-raster-fix` — `6ce011b193fd38cdd37bd8a62a34782f02368efe` — merged/completed — PR #39 (merged)
- [ ] `feat/58-turnstile-contact-icons` — `ec9339b748e2eacf862804c8a3dfc12aa3ff320b` — merged/completed — PR #60 (merged)
- [ ] `fix/111-deepseek-v4-contract` — `91058c85508a7ee7b401dcaa0634aab584a5f133` — merged/completed — PR #120 (merged)
- [ ] `fix/112-chat-retention-expiry-v2` — `682a66a7db419cf151502224646c4d0437f2b9c5` — merged/completed — PR #124 (merged)
- [ ] `fix/42-remove-cv-cloudflare-ownership` — `17048fcf563c16f9add8b4bde5bdea0acc55056e` — merged/completed — PR #43 (merged)
- [ ] `fix/44-pin-compose-file` — `d061e9efa314217e61d408c2a5e90d261b51d60d` — merged/completed — PR #45 (merged)
- [ ] `fix/47-loopback-cv-origin` — `c46f01c5b7f4f3a14f27f318afb85377d34438e5` — merged/completed — PR #48 (merged)
- [ ] `fix/49-loopback-deploy-health` — `f19b4260005e6c1464bbd86158fc6faa2031daf1` — merged/completed — PR #50 (merged)
- [ ] `fix/51-browser-smoke-link-state` — `92c13a49cd1c52e25f005afa58d5191f2edf705b` — merged/completed — PR #69 (merged)
- [ ] `fix/52-nginx-mjs-mime` — `2635c952fb0513d3c411f3a2062cb531288bd547` — merged/completed — PR #53 (merged)
- [ ] `fix/54-nginx-config-recreate` — `89191a2b571d2b510f8f8c96784b0256ea79e6b4` — merged/completed — PR #55 (merged)
- [ ] `fix/56-restore-rich-cv-layout` — `8d346674177bdce680254ea4b25a0baa20e10dfc` — merged/completed — PR #57 (merged)
- [ ] `fix/58-live-stats-contact-turnstile` — `b09a785cad251d85126934f16d7865a054a6af92` — merged/completed — PR #59 (merged)
- [ ] `fix/58-live-stats-runtime-contract` — `27f3610517f215819319373b3f4deba59090090e` — merged/completed — PR #61 (merged)
- [ ] `fix/62-live-stats-systemd` — `35e8fcc4a1c1bf0f56bd1caffa1a2b198f8cb940` — merged/completed — PR #63 (merged)
- [ ] `fix/64-stats-shell-exec` — `08271aa50fe8656b957934d1a4dbf8d110021921` — merged/completed — PR #65 (merged)
- [ ] `fix/66-prometheus-endpoint-discovery` — `52ccbabb424d3f8203b322c6dbe2cd00929821cc` — merged/completed — PR #67 (merged)
- [ ] `fix/77-portable-public-header-parse-v01` — `44314f191d1487b242979d2ca373d86464eee210` — merged/completed — PR #78 (merged)
- [ ] `fix/94-public-email-whatsapp-qr-v4` — `0c0506912d015c9ecae9529ac56f55c0cc537541` — merged/completed — PR #119 (merged)
- [ ] `fix/assistant-request-safety-v01` — `0112bccf6a0af8b2e9c1c5071141af67a203b00f` — merged/completed — PR #21 (merged)
- [ ] `fix/baseline-deploy-health-evidence-v01` — `34c2efc7cf389646706c113dfa85dbb01ee435d1` — merged/completed — PR #2 (merged)
- [ ] `fix/cloudflared-edge-ready-canary` — `fe7fbcc3bd94ed104b1a36f768339b99b020a1f8` — merged/completed — PR #40 (merged)
- [ ] `fix/cloudflared-runtime-reconcile` — `ba70841235fe01645b29c180f430316bd2c962d2` — merged/completed — PR #36 (merged)
- [ ] `fix/cvbot-runtime-security-evidence` — `874fb3076a7a83eda3d4be0a9be24f4ec2cbd460` — merged/completed — PR #37 (merged)
- [ ] `fix/deploy-compose-env-static-permissions-v01` — `e1185790820a8cc11ba77fb8e33d852598453148` — merged/completed — PR #4 (merged)
- [ ] `fix/deterministic-live-stats-v01` — `37661fab25ca2a84ad9a28bf08b5e29c26a2dc0d` — merged/completed — PR #23 (merged)
- [ ] `fix/pin-effective-compose-network-v01` — `82e503ed75bd3c0e3c7218fd220d76631b892ef9` — merged/completed — PR #20 (merged)
- [ ] `fix/supply-chain-hardening-v02` — `1dcbd75f0d44a9b1a345b46f6577fdbf5783c1c4` — merged/completed — PR #32 (merged)
- [ ] `fix/transactional-deploy-retention-v01` — `706b53857c322efa88d2bb20b4739558a2df66b4` — merged/completed — PR #19 (merged)
- [ ] `perf/82-reduce-initial-background-work-v01` — `496cf35bb580c25a0ab1d72c7ba31e8302c41b68` — merged/completed — PR #83 (merged)
- [ ] `perf/86-static-payload-cache-v01` — `f25b52781c19bed32a928c5a60e8a669ff4a9f77` — merged/completed — PR #87 (merged)
- [ ] `refactor/72-frontend-source-dist-v01` — `0a46fab15e5503f45f966d982c649be0958b3899` — merged/completed — PR #73 (merged)
- [ ] `refactor/75-unify-i18n-features-v01` — `4b49478b2429467ed82c7c5c9455673fd7bfb4d7` — merged/completed — PR #76 (merged)
- [ ] `refactor/80-consolidate-css-v01` — `d7d8dad46990523650cafe141da31bbf88c817eb` — merged/completed — PR #81 (merged)
- [ ] `refactor/canonical-cv-content-v01` — `f6deefb091a4f35da30e2ea0393c87ab0eded8b9` — merged/completed — PR #26 (merged)
- [ ] `refactor/frontend-accessibility-v01` — `9b2ba2eee864ba2402c3dd6b19247733275b0728` — merged/completed — PR #25 (merged)
- [ ] `security/94-current-contact-literals-v01` — `7680ade3765a4837e3c569b6ab9540aab0d05ac8` — merged/completed — PR #105 (merged)
- [ ] `security/remove-contact-literals-public-readiness` — `3af9cc93883ec4e57e0ae47109832ac01225d8c2` — merged/completed — PR #74 (merged)
- [ ] `test/browser-behavior-ci-v02` — `a1eb45a5c202caea72bb112cd53f82b8ca609016` — merged/completed — PR #31 (merged)
- [ ] `test/frontend-rpi5-readonly-v01` — `57000f283f97f1a06b6803c89aeaef82592a390e` — merged/completed — PR #28 (closed)

**Safety gate:** re-run the inventory immediately before any deletion. Delete only branches still in the owner-approved candidate set, using normal branch deletion. Never force-move a branch ref as a substitute for deletion.

## Unique/elevated branches requiring explicit review

- `audit/88-history-scope-v01` — review-before-delete — sensitive-surface paths: `.github/workflows/88-address-shape-audit.yml`, `.github/workflows/88-history-scope-audit.yml`
- `audit/94-production-proof-v01` — review-before-delete — sensitive-surface paths: `.github/workflows/94-production-proof.yml`
- `chore/remove-legacy-source-writers-v01` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `scripts/validate-source.sh`
- `feat/58-turnstile-contact-icons` — delete-candidate — sensitive-surface paths: `bot/.env.example`, `bot/Dockerfile`, `bot/app.py`, `bot/contact.py`, `docker-compose.yml`, `nginx.conf`, `scripts/build-input-id.py`
- `fix/111-deepseek-v4-contract` — delete-candidate — sensitive-surface paths: `bot/.env.example`, `bot/app.py`
- `fix/112-chat-retention` — preserve-review — sensitive-surface paths: `bot/.env.example`, `bot/app.py`, `bot/storage.py`
- `fix/112-chat-retention-expiry` — review-before-delete — sensitive-surface paths: `bot/.env.example`, `bot/app.py`, `bot/storage.py`
- `fix/112-chat-retention-expiry-v2` — delete-candidate — sensitive-surface paths: `bot/.env.example`, `bot/app.py`, `bot/storage.py`
- `fix/113-dedicated-client-secret` — review-before-delete — sensitive-surface paths: `bot/.env.example`, `bot/app.py`, `bot/storage.py`, `runner/release/rozkalns-cv-deploy-main`
- `fix/42-remove-cv-cloudflare-ownership` — delete-candidate — sensitive-surface paths: `docker-compose.yml`, `runner/release/rozkalns-cv-deploy-main`, `scripts/validate-source.sh`
- `fix/44-pin-compose-file` — delete-candidate — sensitive-surface paths: `runner/release/rozkalns-cv-deploy-main`
- `fix/47-loopback-cv-origin` — delete-candidate — sensitive-surface paths: `docker-compose.yml`
- `fix/49-loopback-deploy-health` — delete-candidate — sensitive-surface paths: `runner/release/rozkalns-cv-deploy-main`
- `fix/52-nginx-mjs-mime` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `nginx.conf`
- `fix/52-nginx-mjs-mime-clean` — preserve-review — sensitive-surface paths: `.github/workflows/ci.yml`, `nginx.conf`
- `fix/54-nginx-config-recreate` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `.github/workflows/deploy-main.yml`, `docker-compose.yml`, `nginx.conf`
- `fix/62-live-stats-systemd` — delete-candidate — sensitive-surface paths: `scripts/install-live-stats-systemd.sh`
- `fix/64-stats-shell-exec` — delete-candidate — sensitive-surface paths: `scripts/install-live-stats-systemd.sh`
- `fix/66-prometheus-endpoint-discovery` — delete-candidate — sensitive-surface paths: `scripts/install-live-stats-systemd.sh`, `scripts/resolve-prometheus.py`
- `fix/77-portable-public-header-parse-v01` — delete-candidate — sensitive-surface paths: `.github/workflows/deploy-main.yml`
- `fix/94-public-email-verified-whatsapp-v3` — review-before-delete — sensitive-surface paths: `.github/workflows/c94-finalizer-repair.yml`, `.github/workflows/c94-focused-diagnostic.yml`, `.github/workflows/c94-pdf-layout-audit.yml`, `bot/contact.py`, `scripts/c94-apply-public-contact.py`
- `fix/94-public-email-whatsapp-qr-v4` — delete-candidate — sensitive-surface paths: `bot/app.py`, `bot/system_prompt.txt`, `scripts/build-content.py`
- `fix/assistant-request-safety-v01` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `bot/.env.example`, `bot/Dockerfile`, `bot/app.py`, `bot/storage.py`, `docker-compose.yml`, `nginx.conf`, `scripts/purge-chat-data.py`
- `fix/baseline-deploy-health-evidence-v01` — delete-candidate — sensitive-surface paths: `runner/release/rozkalns-cv-deploy-main`
- `fix/cloudflared-edge-ready-canary` — delete-candidate — sensitive-surface paths: `docker-compose.yml`, `runner/release/rozkalns-cv-deploy-main`
- `fix/cloudflared-runtime-reconcile` — delete-candidate — sensitive-surface paths: `runner/release/rozkalns-cv-deploy-main`
- `fix/cvbot-runtime-security-evidence` — delete-candidate — sensitive-surface paths: `runner/release/rozkalns-cv-deploy-main`
- `fix/deploy-compose-env-static-permissions-v01` — delete-candidate — sensitive-surface paths: `runner/release/rozkalns-cv-deploy-main`
- `fix/deterministic-live-stats-v01` — delete-candidate — sensitive-surface paths: `scripts/generate-stats.py`
- `fix/pin-effective-compose-network-v01` — delete-candidate — sensitive-surface paths: `docker-compose.yml`, `runner/release/rozkalns-cv-deploy-main`, `scripts/validate-source.sh`
- `fix/supply-chain-hardening-v01` — review-before-delete — sensitive-surface paths: `.github/workflows/ci.yml`, `.github/workflows/resolve-supply-chain-v05.yml`, `bot/Dockerfile`, `bot/requirements.in`, `docker-compose.yml`, `scripts/build-input-id.py`, `scripts/run-gitleaks.sh`
- `fix/supply-chain-hardening-v02` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `.github/workflows/deploy-main.yml`, `bot/Dockerfile`, `bot/requirements.in`, `bot/requirements.lock`, `bot/requirements.txt`, `docker-compose.yml`, `runner/release/rozkalns-cv-deploy-main`, +2 more
- `fix/transactional-deploy-retention-v01` — delete-candidate — sensitive-surface paths: `runner/release/rozkalns-cv-deploy-main`
- `perf/82-reduce-initial-background-work-v01` — delete-candidate — sensitive-surface paths: `scripts/check-frontend-dist.mjs`
- `perf/86-static-payload-cache-v01` — delete-candidate — sensitive-surface paths: `docker-compose.yml`, `nginx.conf`, `scripts/check-frontend-dist.mjs`
- `rebuild/canonical-on-main-v01` — preserve-review — sensitive-surface paths: `bot/app.py`, `bot/system_prompt.txt`
- `refactor/72-frontend-source-dist-v01` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `scripts/build-content.py`, `scripts/build-frontend.mjs`, `scripts/check-frontend-dist.mjs`, `scripts/validate-source.sh`
- `refactor/75-unify-i18n-features-v01` — delete-candidate — sensitive-surface paths: `scripts/check-frontend-dist.mjs`, `scripts/validate-source.sh`
- `refactor/80-consolidate-css-v01` — delete-candidate — sensitive-surface paths: `.github/workflows/c4-visual-equivalence.yml`, `scripts/check-frontend-dist.mjs`, `scripts/validate-source.sh`
- `refactor/canonical-cv-content-v01` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `bot/app.py`, `bot/system_prompt.txt`, `nginx.conf`, `scripts/build-content.py`, `scripts/sync-system-prompt.py`, `scripts/validate-source.sh`
- `refactor/frontend-accessibility-v01` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `nginx.conf`
- `security/94-current-contact-literals-v01` — delete-candidate — sensitive-surface paths: `bot/app.py`, `bot/system_prompt.txt`, `scripts/bootstrap-github.sh`, `scripts/build-content.py`
- `security/remove-contact-literals-public-readiness` — delete-candidate — sensitive-surface paths: `bot/contact.py`
- `test/browser-behavior-ci-v01` — review-before-delete — sensitive-surface paths: `.github/workflows/ci.yml`, `nginx.conf`, `scripts/run-python-tests.py`
- `test/browser-behavior-ci-v02` — delete-candidate — sensitive-surface paths: `.github/workflows/ci.yml`, `scripts/run-python-tests.py`
