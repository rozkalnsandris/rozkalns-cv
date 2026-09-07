# Engineering case study: when a valid redirect broke release verification

> **Historical scope:** this case study describes a source/release incident recorded on
> 2026-09-01. It is engineering evidence, not a statement about the current production
> deployment, runtime state, provider configuration, or rollout eligibility.

A deliberate web-routing change exposed a stale assumption in the transactional release
verifier. The failure was bounded, the previous application state was restored, and the
verifier contract was corrected with focused regression coverage. The example is useful
because the failure was not in the new page behavior itself: it was in automation that
still encoded the old behavior.

## 1. Context and expected contract

The localized site intentionally changed the root request from a page response to an HTTP
308 redirect to `/en/`. Release verification still had to prove that the root policy was
exact, that the localized page was fetchable, and that the page and hashed frontend module
kept their security/content contracts.

**Evidence:** [PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405),
[audit #399](https://github.com/rozkalnsandris/rozkalns-cv/issues/399), and the
[current verifier source](../runner/release/rozkalns-cv-pull-deploy-main).

## 2. Symptom: the verifier rejected valid site behavior

The public record for PR #405 states that a manual rollout reached the target application
but failed during public frontend contract verification. The transaction then restored the
previous application baseline. The failure therefore provided a concrete release signal
without being treated as permission to weaken the verifier.

**Evidence:** [PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405) and
[audit #399](https://github.com/rozkalnsandris/rozkalns-cv/issues/399).

## 3. Evidence that isolated the failure layer

The pre-fix verifier fetched the public root without following redirects and immediately
searched that response body for the hashed frontend module. After the root became a 308
redirect, the verifier was inspecting a redirect response as if it were page HTML. That
narrow mismatch explained why valid routing could fail the release contract.

**Evidence:** the before/after diff and root-cause note in
[PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405).

## 4. Root cause

The automation encoded an obsolete response-shape assumption: `PUBLIC_URL` was expected to
return the canonical page body directly. The application contract had deliberately changed,
but the release verifier contract had not changed with it.

**Evidence:** [PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405) and
[audit #399](https://github.com/rozkalnsandris/rozkalns-cv/issues/399).

## 5. Smallest coherent source fix

The fix did not blindly enable redirect following. It made the routing contract explicit:
verify the root status is 308, verify the `Location` is the expected same-site `/en/`
target, then fetch the localized page and validate the page/module contracts there. The
current verifier retains that separation between redirect validation and page validation.

**Evidence:** [PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405) and the
[current verifier source](../runner/release/rozkalns-cv-pull-deploy-main).

## 6. Regression prevention

A focused source test locks the intentional redirect semantics and checks that page-header
validation occurs after the redirect boundary. Later hardening extended that same test
surface without removing the original exact-status and exact-target contract.

**Evidence:** [redirect contract tests](../tests/test_pull_deploy_public_redirect_contract.py)
and [PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405).

## 7. Release and rollback boundary

The corrective PR was source/tests work only; it did not authorize a production mutation.
The earlier failed transaction is recorded as having restored the previous application
baseline, while subsequent deployment decisions remained separately gated. This distinction
matters: a source fix can be ready and validated without proving that it is currently live.

**Evidence:** [PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405) and
[audit #399](https://github.com/rozkalnsandris/rozkalns-cv/issues/399).

## 8. Defensible lessons

- Treat release verification as versioned code: when an intentional application contract
  changes, update the verifier and its tests in the same evidence trail.
- Prefer exact contract checks over permissive workarounds. Here, validating the expected
  308 and target preserved a stronger boundary than simply following any redirect.
- A rollback is evidence that a transactional guard worked; it is not a reason to bypass
  the failing gate on the next attempt.
- Keep source readiness separate from production state. Repository evidence can prove the
  verifier implementation and tests, but it cannot by itself prove what is currently live.

**Evidence:** [PR #405](https://github.com/rozkalnsandris/rozkalns-cv/pull/405),
[audit #399](https://github.com/rozkalnsandris/rozkalns-cv/issues/399), the
[current verifier source](../runner/release/rozkalns-cv-pull-deploy-main), and the
[redirect contract tests](../tests/test_pull_deploy_public_redirect_contract.py).

## Publication boundary

This case study intentionally uses only public repository evidence. It omits private logs,
credentials, account identifiers, internal network topology, private job-search context and
unverified impact metrics. Historical statements above are dated and must not be reused as
claims about current production state.
