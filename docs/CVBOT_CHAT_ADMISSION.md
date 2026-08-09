# CV assistant chat admission

The public CV assistant requires a one-time Turnstile admission before the first provider-backed chat turn.

- The browser uses the dedicated Turnstile action `chat_admission`; contact reveal continues to use `contact_reveal`.
- The server validates the token with Cloudflare Siteverify, including the expected action, configured hostname and normalized client address.
- Turnstile tokens are consumed only by `/chat-admission`; they are never reused for contact reveal or `/chat`.
- After successful validation, the server issues a 15-minute HMAC-signed admission session bound to the pseudonymous client identity.
- Copying that session to a different source address fails because the pseudonymous client binding changes.
- The admission session is not an unlimited API credential: the existing durable per-client hourly cap and daily global cap remain authoritative.
- `/chat` validates admission before the original handler can reserve quota. Invalid, expired or missing admission therefore cannot consume the provider allowance.
- Siteverify transport failures fail closed and direct the visitor to the public recruiting email path.
- The Turnstile script remains lazy and is loaded only when chat is first used, not on every page view.

Cloudflare Turnstile tokens are single-use and expire after five minutes; the short server-issued session exists only to avoid repeating a challenge for every turn in one normal conversation.
