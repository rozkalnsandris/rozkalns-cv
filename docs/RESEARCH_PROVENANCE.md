# Research provenance and confidence

## Claude history

A structured Claude export analysis was found in the File Library. It covers
269 conversations, 9,923 messages and 180 extracted attachments from
2026-04-18 through 2026-07-16.

The most relevant CV conversations in its index are:

- 2026-06-25 — `CV izskates uzlabošana` (108 messages)
- 2026-06-24 — `CV ar AI` (150 messages)
- 2026-07-13 — `CV lapas SEO optimizācija ar AI`

The export also contains historical RPi5 audits and terminal output that confirm
the nginx, CV assistant, metrics, Docker Compose and Cloudflare Tunnel design.

## Gemini history

No distinct, trustworthy Gemini export or Gemini conversation archive about the
CV project was found in the currently available File Library after searches for
Gemini export, Google Takeout, Gemini Apps Activity, conversations JSON,
`rozkalns.net`, CV and portfolio terms.

Unrelated references to Gemini models were ignored. They are not evidence about
the CV project. If a separate Gemini export is uploaded later, it should be
analyzed and reconciled against this repository's project documentation.

## Source-of-truth rule

Chat histories are design and decision evidence, not authoritative live source.
The current `/home/andris/docker/cv` files on the RPi5 are the authoritative
baseline for the initial Git import. The exporter copies that baseline and then
adds only repository operations, validation and deployment files.

Historical claims that conflict with current RPi5 files or runtime checks must
be treated as stale until independently verified.
