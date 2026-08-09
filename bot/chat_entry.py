from __future__ import annotations

from flask import jsonify, request

import app as base
from chat_admission import (
    ChatAdmissionConfig,
    ChatAdmissionError,
    issue_session,
    validate_session,
    verify_chat_turnstile,
)

app = base.app
ADMISSION_CONFIG = ChatAdmissionConfig(
    site_key=base.CONTACT_CONFIG.site_key,
    secret_key=base.CONTACT_CONFIG.secret_key,
    hostnames=base.CONTACT_CONFIG.hostnames,
)
_original_chat = app.view_functions["chat"]


def _client_identity() -> tuple[str, str]:
    address = base._resolve_client_address()
    return address, base.STORE.pseudonymize(address, base.CLIENT_KEY_SECRET)


@app.get("/chat-config")
def chat_config():
    response = jsonify(
        configured=ADMISSION_CONFIG.configured,
        sitekey=ADMISSION_CONFIG.site_key if ADMISSION_CONFIG.configured else "",
        action="chat_admission",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/chat-admission")
def chat_admission():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(reply="Verification is required before chat."), 400
    address, client_key = _client_identity()
    try:
        valid = verify_chat_turnstile(payload.get("token"), address, ADMISSION_CONFIG)
    except ChatAdmissionError as error:
        base.app.logger.error("chat admission unavailable: %s", type(error).__name__)
        return jsonify(reply="Chat verification is temporarily unavailable. Please email Andris instead."), 503
    if not valid:
        return jsonify(reply="Chat verification failed. Please try again."), 403
    response = jsonify(session=issue_session(client_key, base.CLIENT_KEY_SECRET))
    response.headers["Cache-Control"] = "no-store"
    return response


def protected_chat():
    _address, client_key = _client_identity()
    session = request.headers.get("X-Chat-Admission", "")
    if not validate_session(session, client_key, base.CLIENT_KEY_SECRET):
        return jsonify(reply="Chat verification is required or has expired."), 401
    return _original_chat()


app.view_functions["chat"] = protected_chat
