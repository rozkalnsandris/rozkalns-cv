# FAST-LANE v2.2 Composite — rozkalns-cv

> Compatibility path: `AGENTS.md` already points to this v2.1 filename; these are the authoritative v2.2 rules.

## Core rule

**The human approves the RISK / DECISION. Automation executes the TECHNICAL STEPS.** Read-only checkpoints never create owner gates; STRICT describes live risk, not approval-per-command.

## FAST

Documentation/content, site/application source, tests and deterministic refactors may proceed from fresh GitHub state through Ready in one batch, including branch, PR, CI/review and up to two scope-preserving corrections. Batch 2-5 related same-risk items when coherent. Merge remains explicit.

## Human gate budget and Composite STRICT

Normal delivery has at most two owner gates: **MERGE**, then **COMPOSITE LIVE** only when production/live mutation is required. Before the live gate, gather all read-only evidence. One bounded authorization binds exact SHA, exact target, allowed mutation categories, limits, exclusions and expected baseline; preflight and verification execute inside one fail-closed one-shot.

For deploy artifacts/versions, use pinned tooling, build once, verify the exact candidate, re-check production drift and deploy that exact verified artifact/version. Do not silently switch to newer `main`.

## Local STRICT boundaries

Production deploy/pull-deploy activation, Cloudflare production changes, credentials/secrets, host/runtime mutation, production data writes, permission expansion or another live authority change require Composite Live authorization.

## Failure and evidence

Authorization is consumed at first authorized mutation. Any later error/ambiguity requires evidence preservation and STOP; no automatic retry, rollback, cleanup or alternate mutation path unless explicitly pre-authorized.

Use one Ready receipt and one final live receipt. Put any remaining owner decision at the **end** under `ACTION REQUIRED`; when the owner must enter/run something, provide the exact copyable instruction in a fenced `bash` block.

Merge never authorizes deployment or another live mutation.
