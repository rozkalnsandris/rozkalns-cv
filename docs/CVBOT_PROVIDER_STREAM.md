# CV assistant provider stream contract

cvbot treats DeepSeek chat streaming as a finite protocol, not as best-effort text parsing.

## Stream lifecycle

The provider request uses `stream=true` and `stream_options.include_usage=true`. Every non-empty SSE record must be a `data:` record containing either a documented chat-completion chunk or the final `[DONE]` marker.

A successful request requires both a documented terminal `finish_reason` and `[DONE]`. Empty deltas are harmless. Malformed JSON, invalid choice/delta shapes, duplicate or unknown terminal states, `[DONE]` before a terminal state, and upstream EOF before `[DONE]` are protocol failures.

Visitor behavior is explicit:

- `stop`: normal answer; eligible for retention/Telegram under the existing policy.
- `length`: already-streamed partial text may remain visible, followed by a truncation notice; it is not retained/notified as a complete answer.
- `content_filter`: a safety notice is emitted; the response is not retained/notified as complete.
- `insufficient_system_resource`: a temporary-capacity notice is emitted; the response is not retained/notified as complete.
- `tool_calls`: unsupported for this tool-free CV assistant and treated as a failed provider outcome.
- malformed stream, early EOF, timeout, HTTP failure or browser disconnect: never retained/notified as a successful answer.
- protected phone/WhatsApp output remains a local policy completion: the unsafe provider fragment is suppressed and only the deterministic safe replacement is eligible for retention/notification.

## Timeout ownership

The timeout chain is intentionally ordered:

1. provider TCP/TLS connect timeout: 5 seconds;
2. provider idle-read timeout: 70 seconds;
3. Gunicorn worker timeout: 90 seconds;
4. Nginx `proxy_read_timeout`: 120 seconds.

The provider client therefore owns connect/read failure first. Gunicorn remains above the provider idle-read budget, and Nginx remains above Gunicorn, avoiding a downstream layer unexpectedly terminating an otherwise valid provider request. The source defaults and `.env.example` values are covered by contract tests.

## Privacy-safe telemetry

Each accepted provider attempt receives a random request correlation ID. The completion log contains only aggregate operational fields: request ID, duration, status class, finish reason, aggregate token counts when supplied by DeepSeek, and remaining quota counts.

Provider telemetry must never contain prompts, answers, raw IP addresses, authorization headers/API keys, Turnstile tokens, runtime phone values, or provider payload bodies.
