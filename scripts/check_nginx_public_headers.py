#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


COMMON_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

NONCE_RE = re.compile(r"nonce-[0-9a-f]{32}")


@dataclass(frozen=True)
class RouteExpectation:
    name: str
    path: str
    status: int
    cache: str
    content_type: str | None = None
    location: str | None = None
    robots: str | None = None


def _manifest_route(manifest: dict, key: str, field: str = "file") -> str:
    value = manifest.get(key, {}).get(field, "")
    if not isinstance(value, str) or not value:
        raise AssertionError(f"manifest route missing: {key}.{field}")
    return "/" + value.lstrip("/")


def build_matrix(manifest: dict) -> tuple[RouteExpectation, ...]:
    module = _manifest_route(manifest, "index.html")
    css_rows = manifest.get("index.html", {}).get("css", [])
    if not isinstance(css_rows, list) or len(css_rows) != 1:
        raise AssertionError(f"expected one index CSS asset, got {css_rows!r}")
    css = "/" + str(css_rows[0]).lstrip("/")
    i18n = _manifest_route(manifest, "../content/translations/en.json")
    photo = _manifest_route(manifest, "photo.webp")

    hashed_module = re.compile(r"^/assets/.+\.[0-9a-f]{12}\.mjs$")
    hashed_static = re.compile(r"^/(?:assets|i18n)/.+\.[0-9a-f]{12}\.(?:css|json|webp)$")
    if not hashed_module.fullmatch(module):
        raise AssertionError(f"module is outside hashed-module route class: {module}")
    for route in (css, i18n, photo):
        if not hashed_static.fullmatch(route):
            raise AssertionError(f"asset is outside hashed-static route class: {route}")

    return (
        RouteExpectation("root-redirect", "/", 308, "not-immutable", location="/en/"),
        RouteExpectation("localized-page", "/en/", 200, "not-immutable", content_type="text/html"),
        RouteExpectation("localized-proof", "/en/proof/", 200, "not-immutable", content_type="text/html"),
        RouteExpectation("smart-home-html", "/smarthome.html", 200, "not-immutable", content_type="text/html"),
        RouteExpectation("stats-json-location", "/stats.json", 404, "not-immutable"),
        RouteExpectation("hashed-module", module, 200, "immutable", content_type="text/javascript"),
        RouteExpectation("hashed-css", css, 200, "immutable", content_type="text/css"),
        RouteExpectation("hashed-i18n-json", i18n, 200, "immutable", content_type="application/json"),
        RouteExpectation("hashed-webp", photo, 200, "immutable", content_type="image/webp"),
        RouteExpectation("favicon-redirect", "/favicon.ico", 308, "not-immutable", location="/favicon.svg"),
        RouteExpectation("regular-static-svg", "/favicon.svg", 200, "one-hour", content_type="image/svg+xml"),
        RouteExpectation(
            "cv-pdf",
            "/cv.pdf",
            200,
            "one-hour",
            content_type="application/pdf",
            robots="noindex, nofollow",
        ),
        RouteExpectation("default-static", "/sitemap.xml", 200, "not-immutable"),
        RouteExpectation("proxied-api-error", "/api/health", 502, "not-immutable"),
    )


def _headers(response: http.client.HTTPResponse) -> dict[str, str]:
    grouped: dict[str, list[str]] = {}
    for name, value in response.getheaders():
        grouped.setdefault(name.lower(), []).append(value.strip())
    return {name: ", ".join(values) for name, values in grouped.items()}


def _assert_common(route: RouteExpectation, headers: dict[str, str]) -> None:
    for name, expected in COMMON_HEADERS.items():
        actual = headers.get(name)
        if actual != expected:
            raise AssertionError(f"{route.name}: {name}={actual!r}, expected {expected!r}")

    csp = headers.get("content-security-policy", "")
    if not csp:
        raise AssertionError(f"{route.name}: missing Content-Security-Policy")
    if not NONCE_RE.search(csp):
        raise AssertionError(f"{route.name}: CSP has no request nonce: {csp!r}")
    for required in (
        "default-src 'self'",
        "frame-ancestors 'none'",
        "script-src-attr 'none'",
        "connect-src 'self'",
    ):
        if required not in csp:
            raise AssertionError(f"{route.name}: CSP missing {required!r}")
    if "unsafe-inline" in csp:
        raise AssertionError(f"{route.name}: CSP unexpectedly allows unsafe-inline")


def _assert_cache(route: RouteExpectation, headers: dict[str, str]) -> None:
    cache = headers.get("cache-control", "").lower()
    if route.cache == "immutable":
        for token in ("public", "max-age=31536000", "immutable"):
            if token not in cache:
                raise AssertionError(f"{route.name}: Cache-Control missing {token!r}: {cache!r}")
    elif route.cache == "one-hour":
        if "max-age=3600" not in cache or "immutable" in cache:
            raise AssertionError(f"{route.name}: expected one-hour non-immutable cache, got {cache!r}")
    elif route.cache == "not-immutable":
        if "immutable" in cache:
            raise AssertionError(f"{route.name}: dynamic/non-hashed response became immutable: {cache!r}")
    else:
        raise AssertionError(f"{route.name}: unknown cache mode {route.cache!r}")


def _request(connection: http.client.HTTPConnection, route: RouteExpectation) -> None:
    connection.request("HEAD", route.path, headers={"Host": "127.0.0.1"})
    response = connection.getresponse()
    headers = _headers(response)
    response.read()

    if response.status != route.status:
        raise AssertionError(f"{route.name}: status={response.status}, expected={route.status}")

    _assert_common(route, headers)
    _assert_cache(route, headers)

    if route.content_type is not None:
        actual = headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if actual != route.content_type:
            raise AssertionError(
                f"{route.name}: Content-Type={actual!r}, expected={route.content_type!r}"
            )

    if route.location is not None:
        actual_location = headers.get("location", "")
        parsed_location = urlsplit(actual_location)
        actual_path = parsed_location.path if parsed_location.path else actual_location
        if actual_path != route.location:
            raise AssertionError(
                f"{route.name}: Location={actual_location!r}, expected path={route.location!r}"
            )

    if route.robots is not None and headers.get("x-robots-tag") != route.robots:
        raise AssertionError(
            f"{route.name}: X-Robots-Tag={headers.get('x-robots-tag')!r}, expected={route.robots!r}"
        )

    print(
        "NGINX_HEADER_MATRIX="
        f"{route.name}:status={response.status}:cache={route.cache}:PASS"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--manifest", default="frontend-dist-manifest.json")
    args = parser.parse_args()

    parsed = urlsplit(args.base_url)
    if parsed.scheme != "http" or not parsed.hostname or parsed.path not in ("", "/"):
        raise SystemExit("--base-url must be an http origin without a path")
    port = parsed.port or 80

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    matrix = build_matrix(manifest)

    connection = http.client.HTTPConnection(parsed.hostname, port, timeout=5)
    try:
        for route in matrix:
            _request(connection, route)
    finally:
        connection.close()

    print(f"NGINX_HEADER_MATRIX_ROUTE_CLASSES={len(matrix)}")
    print("NGINX_HEADER_MATRIX=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
