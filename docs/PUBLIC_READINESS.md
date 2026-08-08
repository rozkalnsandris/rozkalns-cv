# Public-repository readiness

Status: **PUBLIC — remediation in progress**.

The repository is public. Keep the remaining cleanup items below visible until they are resolved.

## Public-readiness gates

- [ ] Complete #94 current-tree contact remediation. Owner decision: the recruiting email is intentionally public; the phone remains runtime-protected; public PDFs use a WhatsApp-marked QR that encodes only the protected-site contact URL and requires server-side Turnstile before a runtime WhatsApp target is returned.
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
- `bot/contact.py` loads real phone/contact runtime values from environment variables and fails closed when required values are absent.
- The recruiting email `andris@rozkalns.net` is intentionally public for CV/job-contact use and may appear in canonical content, assistant knowledge, site output and public PDFs.
- The phone number is classified `verified-runtime`; canonical public source and generated assistant knowledge must not embed it.
- The approved public PDF policy is `verified-public-email-protected-phone`: public email visible, no raw phone or `tel:` link, no direct numbered `wa.me` link, and a QR that decodes only to `https://rozkalns.net/?contact=whatsapp`.
- After a successful server-side Turnstile verification, the backend derives the direct WhatsApp URL from runtime `CONTACT_PHONE_URI`; the direct target is not tracked in Git or encoded in the PDF QR.
- #94 EN/DE/LV candidate PDFs were visually reviewed as four pages each with no observed clipping/overlap and a visible WhatsApp-marked QR on page 1.
- Bounded GitHub-hosted C94 v2 finalizer run `31268937271` passed the current-main integration gates from exact head `b9e6a1a220e254e591d3a35f49d59ffc9586a6c9`: all three PDFs contained the public recruiting email, omitted direct phone and numbered WhatsApp links, and their rasterized QR decoded to the protected-site URL; focused canonical/privacy tests and the frontend dist/cache contract also passed. The finalizer self-removed before publishing integration commit `d7eb4bf86371f24f6244ba141d29c3456778b1a0`.
- The QR SVG is content-hashed and receives the same one-year immutable cache policy as other hashed frontend assets; the dist contract additionally enforces exactly one hashed WhatsApp-contact SVG and a bounded vector-asset budget.
- Historical audit found that the initial imported assistant source contained more precise personal location data than the current public professional profile; #88 owns the history-only disposition and values must not be repeated in public evidence.
- The closed Gate C0 audit branch may remain reachable in public Git history even though its pull request is closed; it should not be treated as an active production workflow.

Current-source remediation (#94), historical personal-data handling (#88), retained evidence review (#89), post-public settings verification (#91), release-runner migration (#90), and branch cleanup (#92) remain separate gates.
