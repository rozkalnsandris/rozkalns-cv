# CV assistant provider stream contract

cvbot treats the OpenAI Responses stream as a finite protocol, not as best-effort text parsing.

## Request contract

The provider sends one streaming `POST /v1/responses` request using `gpt-5.6-luna`.
The request is intentionally narrow:

- `store=false`;
- `reasoning.effort=none`;
- `text.verbosity=low`;
- bounded `max_output_tokens`;
- `truncation=disabled`;
- no tools, conversation object, or `previous_response_id`;
- the validated local HMAC client pseudonym is sent as `safety_identifier`;
- the system prompt is sent as `instructions`, while validated bounded browser history is sent as `input`.

The application therefore owns conversation context and does not require OpenAI server-side conversation state.

## Stream lifecycle

OpenAI Responses streaming uses semantic SSE `event:` / `data:` pairs. The parser requires the event name to match the JSON payload `type` and fails closed on malformed or unknown protocol state.

Only public answer/refusal deltas are forwarded to the visitor:

- `response.output_text.delta` -> answer text;
- `response.refusal.delta` -> refusal text.

Known response-progress and reasoning/summary events are consumed but never forwarded. This keeps provider reasoning content out of the public stream even if such events are emitted unexpectedly.

Terminal behavior is explicit:

- `response.completed`: normal completion when only supported message/reasoning output item types are present;
- `response.incomplete` with `max_output_tokens`: partial text followed by a truncation notice;
- `response.incomplete` with `content_filter`: provider safety notice;
- `response.failed` or top-level `error`: provider-failure notice;
- unexpected tool output: unsupported-provider notice;
- malformed event/data pairs, unknown terminal reasons, duplicate terminal states, or EOF before a semantic terminal event: protocol failure.

No Chat Completions `[DONE]` marker is expected. Aggregate token usage is read from the semantic terminal response when present.

A normal completed answer is eligible for the existing local retention/Telegram policy. Incomplete, provider-failed, protocol-failed, timeout, HTTP-failed, or browser-disconnected attempts are not retained/notified as complete answers. The protected phone/WhatsApp output guard remains a local deterministic policy boundary.

## Timeout ownership

The timeout chain remains intentionally ordered:

1. provider TCP/TLS connect timeout: 5 seconds;
2. provider idle-read timeout: 70 seconds;
3. Gunicorn worker timeout: 90 seconds;
4. Nginx `proxy_read_timeout`: 120 seconds.

The provider client therefore owns connect/read failure first. Gunicorn stays above the provider idle-read budget, and Nginx stays above Gunicorn.

## Privacy-safe telemetry

Each accepted provider attempt receives a random request correlation ID. The completion log contains only aggregate operational fields: request ID, duration, status class, terminal classification, aggregate input/output/total token counts when supplied by OpenAI, and remaining quota counts.

Provider telemetry must never contain prompts, answers, raw IP addresses, authorization headers/API keys, Turnstile tokens, runtime phone values, or provider payload bodies.

Official protocol references:

- https://developers.openai.com/api/docs/guides/streaming-responses
- https://developers.openai.com/api/reference/responses/create
