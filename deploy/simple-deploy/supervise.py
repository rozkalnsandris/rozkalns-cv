#!/usr/bin/env python3
"""Minimal PID 1 supervisor for the single-image SIMPLE-DEPLOY CV runtime."""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path


_RUNTIME_DIRS = (
    "/tmp/nginx/client_temp",
    "/tmp/nginx/proxy_temp",
    "/tmp/nginx/fastcgi_temp",
    "/tmp/nginx/uwsgi_temp",
    "/tmp/nginx/scgi_temp",
)


def _terminate(children: list[subprocess.Popen[bytes]], timeout: float = 10.0) -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(child.poll() is not None for child in children):
            break
        time.sleep(0.1)

    for child in children:
        if child.poll() is None:
            child.kill()
    for child in children:
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


def main() -> int:
    for directory in _RUNTIME_DIRS:
        Path(directory).mkdir(parents=True, exist_ok=True)

    received_signal: int | None = None

    def handle_signal(signum: int, _frame: object) -> None:
        nonlocal received_signal
        received_signal = signum

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGHUP, handle_signal)

    children = [
        subprocess.Popen(
            [
                "gunicorn",
                "-w",
                "1",
                "--threads",
                "4",
                "-b",
                "127.0.0.1:5000",
                "--timeout",
                "90",
                "chat_entry:create_app()",
            ],
            cwd="/app",
        ),
        subprocess.Popen(["nginx", "-g", "daemon off;"]),
    ]

    unexpected_status: int | None = None
    while received_signal is None and unexpected_status is None:
        for child in children:
            status = child.poll()
            if status is not None:
                unexpected_status = status if status != 0 else 1
                break
        if unexpected_status is None:
            time.sleep(0.25)

    _terminate(children)
    if received_signal is not None:
        return 0
    return unexpected_status if unexpected_status is not None else 1


if __name__ == "__main__":
    sys.exit(main())
