FROM python:3.14.6-alpine3.24@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92

ARG APP_UID=10001
ARG APP_GID=10001
ARG VCS_REF=unresolved
ARG BUILD_INPUT_SHA256=unresolved
ARG OPENSSL_APK_VERSION=3.5.8-r0
ARG LIBUUID_APK_VERSION=2.42.3-r1

LABEL org.opencontainers.image.source="https://github.com/rozkalnsandris/rozkalns-cv" \
      org.opencontainers.image.revision="${VCS_REF}" \
      net.rozkalns.cv.build-input-sha256="${BUILD_INPUT_SHA256}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /app

RUN apk add --no-cache --upgrade \
      "libcrypto3=${OPENSSL_APK_VERSION}" \
      "libssl3=${OPENSSL_APK_VERSION}" \
      "libuuid=${LIBUUID_APK_VERSION}"

RUN addgroup -S -g "${APP_GID}" cvbot \
    && adduser -S -D -H -u "${APP_UID}" -G cvbot cvbot

COPY requirements.txt ./requirements.txt
RUN python -m pip install --require-hashes --no-deps -r requirements.txt

COPY --chown=${APP_UID}:${APP_GID} \
    app.py chat_admission.py chat_entry.py chat_policy.py config.py contact.py evidence.py evidence_registry.json \
    notifier.py provider.py provider_capacity.py provider_notices.json provider_stream.py readiness.py storage.py \
    system_prompt.py system_prompt.txt turnstile.py ./
RUN mkdir -p /app/data \
    && chown "${APP_UID}:${APP_GID}" /app/data \
    && chmod 0700 /app/data

USER ${APP_UID}:${APP_GID}

EXPOSE 5000

# Provider idle-read budget is 70s; keep Gunicorn above it and Nginx at 120s.
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "90", "chat_entry:create_app()"]
