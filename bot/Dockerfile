FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /app

RUN groupadd --gid "${APP_GID}" cvbot \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" \
        --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin cvbot

COPY requirements.lock ./requirements.lock
RUN python -m pip install --require-hashes --no-deps -r requirements.lock \
    && rm -rf /root/.cache

COPY --chown=${APP_UID}:${APP_GID} app.py storage.py ./
RUN install -d -o "${APP_UID}" -g "${APP_GID}" -m 0700 /app/data

USER ${APP_UID}:${APP_GID}

EXPOSE 5000

# A single worker keeps streaming behavior simple; SQLite coordinates threads.
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "60", "app:app"]
