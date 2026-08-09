FROM python:3.12.13-alpine3.24@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df

ARG APP_UID=10001
ARG APP_GID=10001
ARG VCS_REF=unresolved
ARG BUILD_INPUT_SHA256=unresolved

LABEL org.opencontainers.image.source="https://github.com/rozkalnsandris/rozkalns-cv" \
      org.opencontainers.image.revision="${VCS_REF}" \
      net.rozkalns.cv.build-input-sha256="${BUILD_INPUT_SHA256}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /app

RUN addgroup -S -g "${APP_GID}" cvbot \
    && adduser -S -D -H -u "${APP_UID}" -G cvbot cvbot

COPY requirements.lock ./requirements.lock
RUN python -m pip install --require-hashes --no-deps -r requirements.lock

COPY --chown=${APP_UID}:${APP_GID} \
    app.py chat_admission.py chat_entry.py chat_policy.py config.py contact.py \
    notifier.py provider.py provider_stream.py readiness.py storage.py ./
RUN mkdir -p /app/data \
    && chown "${APP_UID}:${APP_GID}" /app/data \
    && chmod 0700 /app/data

USER ${APP_UID}:${APP_GID}

EXPOSE 5000

# Provider idle-read budget is 70s; keep Gunicorn above it and Nginx at 120s.
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "90", "chat_entry:app"]
