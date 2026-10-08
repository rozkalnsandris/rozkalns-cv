# SIMPLE-FIRST UI v2: defer public CV Assistant

Issue: #513. This is source work, not a production receipt.

Preserve UI v2, EN/DE/LV, CV PDFs, Linux Lab, accessibility and protected contact.
The public CV Assistant launcher/dialog and lazy import are removed from
frontend source and built language routes. SIMPLE-DEPLOY Nginx rejects exactly
the three assistant routes with HTTP 404: chat, chat-config and chat-admission.
Contact and health APIs remain proxied and covered by tests.

The Python application stays in the one-container image for protected contact
and health checks. The chat source is retained for a possible separately
reviewed future activation. A static-only runtime requires a distinct review
of contact, privacy, target contracts, health checks and host deployment.

The legacy restart-looping cvbot container belongs to RPi5_main#913,
not this source change. This PR does not uninstall it, access application data,
repair GHCR production pointer resolution, merge or deploy.
