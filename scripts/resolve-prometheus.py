#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import os
import subprocess
from urllib.parse import urlsplit, urlunsplit


class ResolutionError(RuntimeError):
    pass


def normalize_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ResolutionError("Prometheus URL override is empty")

    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ResolutionError("Prometheus URL must use http or https")
    if not parsed.hostname:
        raise ResolutionError("Prometheus URL is missing a host")
    if parsed.username is not None or parsed.password is not None:
        raise ResolutionError("Prometheus URL must not contain credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ResolutionError("Prometheus URL must not contain a path, query, or fragment")

    try:
        port = parsed.port
    except ValueError as error:
        raise ResolutionError("Prometheus URL contains an invalid port") from error

    host = parsed.hostname
    rendered_host = f"[{host}]" if ":" in host else host
    netloc = rendered_host if port is None else f"{rendered_host}:{port}"
    return urlunsplit((parsed.scheme, netloc, "", "", ""))


def endpoint_from_binding(binding: str) -> str:
    row = binding.strip()
    if not row:
        raise ResolutionError("Prometheus Docker port binding is empty")

    host, separator, port_text = row.rpartition(":")
    if not separator or not host or not port_text.isdigit():
        raise ResolutionError(f"invalid Prometheus Docker port binding: {row}")

    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]

    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise ResolutionError(f"invalid Prometheus Docker bind address: {host}") from error

    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ResolutionError(f"invalid Prometheus Docker bind port: {port}")

    if address.is_unspecified:
        address = ipaddress.ip_address("127.0.0.1" if address.version == 4 else "::1")

    rendered_host = f"[{address}]" if address.version == 6 else str(address)
    return f"http://{rendered_host}:{port}"


def endpoint_from_docker_output(output: str) -> str:
    candidates = {
        endpoint_from_binding(line)
        for line in output.splitlines()
        if line.strip()
    }
    if not candidates:
        raise ResolutionError("Prometheus has no published 9090/tcp binding")
    if len(candidates) != 1:
        raise ResolutionError(
            "Prometheus has multiple distinct published 9090/tcp bindings: "
            + ", ".join(sorted(candidates))
        )
    return next(iter(candidates))


def docker_endpoint() -> str:
    try:
        completed = subprocess.run(
            ["docker", "port", "prometheus", "9090/tcp"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ResolutionError("could not inspect Prometheus Docker port binding") from error
    return endpoint_from_docker_output(completed.stdout)


def resolve() -> str:
    override = os.environ.get("PROMETHEUS_URL")
    if override is not None:
        return normalize_url(override)
    return docker_endpoint()


def main() -> int:
    try:
        endpoint = resolve()
    except ResolutionError as error:
        print(f"PROMETHEUS_RESOLUTION_ERROR={error}", file=os.sys.stderr)
        return 1
    print(endpoint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
