# CV frontend architecture

The public frontend is intentionally framework-free and consists of semantic
HTML plus small, independently cached CSS, JavaScript, and translation assets.
There is no Node.js production server and no runtime build step on the RPi5.

## Authored files

- `html/index.html` — accessible CV document shell;
- `html/smarthome.html` — static portfolio demonstration;
- `html/assets/*.css` — shared responsive presentation;
- `html/assets/*.mjs` — browser behavior;
- `html/i18n/*.json` — EN/DE/LV copy;
- `nginx.conf` — strict CSP and cache policy.

Asset names contain the first 12 hexadecimal characters of the file's SHA-256
digest. Content changes therefore require a new filename and all references to
that filename to be updated in the same commit. CI recomputes every digest and
rejects stale names.

## Security boundary

The site must operate with:

```text
script-src 'self' https://static.cloudflareinsights.com
style-src 'self'
```

Inline scripts, inline styles, event-handler attributes, `unsafe-inline`, and
`unsafe-eval` are forbidden. Fingerprinted assets are served with a one-year
immutable cache lifetime. HTML and `stats.json` remain fresh.

## Chat request contract

The browser sends:

```json
{
  "message": "the current question",
  "history": [
    {"role": "user", "content": "a completed prior question"},
    {"role": "assistant", "content": "its completed answer"}
  ]
}
```

The current question must never appear in `history`. A new history pair is
added only after the response stream finishes successfully. HTTP/network errors
do not leave an unpaired user turn.

## Statistics contract

The browser validates the complete response before rendering it. Invalid JSON,
missing fields, non-finite numbers, malformed timestamps, and timestamps more
than five minutes in the future are treated as offline. Valid data older than
15 minutes is marked cached/stale.

## Accessibility contract

The assistant follows a modal-dialog pattern:

- `aria-modal`, labelled title, and described privacy notice;
- focus moves into the dialog and is trapped while open;
- Escape and the close button dismiss it;
- the background becomes inert;
- focus returns to the launcher;
- response status is exposed without announcing every streamed token;
- language buttons expose `aria-pressed`.

Manual keyboard verification should cover Tab, Shift+Tab, Enter, Escape, and
focus return at desktop and mobile viewport widths.

## Validation

CI executes:

- Python HTML/security/accessibility/content-hash contracts;
- `node --check` for both modules;
- Node behavior tests for chat history and stats validation;
- real `nginx -t`;
- cvbot image build;
- documented frontend size budgets.
