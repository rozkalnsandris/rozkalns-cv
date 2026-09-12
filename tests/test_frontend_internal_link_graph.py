from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import posixpath
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
HTML_ROOT = ROOT / "html"
INTERNAL_HOSTS = {"rozkalns.net", "www.rozkalns.net"}
REFERENCE_ATTRIBUTES = {"href", "src"}


@dataclass
class HtmlDocument:
    path: Path
    ids: set[str] = field(default_factory=set)
    references: list[tuple[str, str, str]] = field(default_factory=list)


class ReferenceParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.document = HtmlDocument(path=path)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._capture(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._capture(tag, attrs)

    def _capture(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value for name, value in attrs if value is not None}
        element_id = values.get("id")
        if element_id:
            self.document.ids.add(element_id)
        if tag.lower() == "a" and values.get("name"):
            self.document.ids.add(values["name"])
        for attribute in REFERENCE_ATTRIBUTES:
            value = values.get(attribute)
            if value is not None:
                self.document.references.append((tag.lower(), attribute, value.strip()))


def _route_aliases(relative: PurePosixPath) -> set[str]:
    absolute = f"/{relative.as_posix()}"
    aliases = {absolute}
    if relative.name == "index.html":
        parent = relative.parent.as_posix()
        directory = "/" if parent == "." else f"/{parent}/"
        aliases.add(directory)
        if directory != "/":
            aliases.add(directory.rstrip("/"))
    return aliases


def _document_url(relative: PurePosixPath) -> str:
    if relative.name == "index.html":
        parent = relative.parent.as_posix()
        return "/" if parent == "." else f"/{parent}/"
    return f"/{relative.as_posix()}"


def _normalize_local_path(source_url: str, reference_path: str) -> str:
    if not reference_path:
        return source_url

    decoded = unquote(reference_path)
    keep_trailing_slash = decoded.endswith("/")
    if decoded.startswith("/"):
        normalized = posixpath.normpath(decoded)
    else:
        base = source_url if source_url.endswith("/") else posixpath.dirname(source_url) + "/"
        normalized = posixpath.normpath(posixpath.join(base, decoded))

    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if keep_trailing_slash and normalized != "/":
        normalized += "/"
    return normalized


def _local_reference(source_url: str, raw: str) -> tuple[str, str] | None:
    if not raw:
        return source_url, ""

    parsed = urlsplit(raw)
    if parsed.netloc:
        host = (parsed.hostname or "").lower()
        if host not in INTERNAL_HOSTS:
            return None
    elif parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https"}:
            return None
        host = (parsed.hostname or "").lower()
        if host not in INTERNAL_HOSTS:
            return None

    target = _normalize_local_path(source_url, parsed.path)
    return target, unquote(parsed.fragment)


def validate_internal_graph(html_root: Path) -> list[str]:
    html_paths = sorted(path for path in html_root.rglob("*.html") if path.is_file())
    documents: dict[Path, HtmlDocument] = {}
    route_to_document: dict[str, Path] = {}
    site_files: set[str] = set()

    for path in sorted(item for item in html_root.rglob("*") if item.is_file()):
        relative = PurePosixPath(path.relative_to(html_root).as_posix())
        site_files.add(f"/{relative.as_posix()}")

    for path in html_paths:
        relative = PurePosixPath(path.relative_to(html_root).as_posix())
        parser = ReferenceParser(path)
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        documents[path] = parser.document
        for route in _route_aliases(relative):
            route_to_document[route] = path

    errors: list[str] = []
    for path, document in documents.items():
        relative = PurePosixPath(path.relative_to(html_root).as_posix())
        source_url = _document_url(relative)
        source_label = relative.as_posix()

        for tag, attribute, raw in document.references:
            resolved = _local_reference(source_url, raw)
            if resolved is None:
                continue
            target_url, fragment = resolved
            target_document = route_to_document.get(target_url)
            target_is_file = target_url in site_files

            if target_document is None and not target_is_file:
                errors.append(
                    f"{source_label}: <{tag}> {attribute}={raw!r} points to missing local target {target_url!r}"
                )
                continue

            if fragment and target_document is not None:
                target_relative = target_document.relative_to(html_root).as_posix()
                if fragment not in documents[target_document].ids:
                    errors.append(
                        f"{source_label}: {attribute}={raw!r} points to missing fragment #{fragment} in {target_relative}"
                    )

    return errors


class FrontendInternalLinkGraphTests(unittest.TestCase):
    def test_generated_public_site_has_no_broken_internal_references(self) -> None:
        errors = validate_internal_graph(HTML_ROOT)
        self.assertEqual(errors, [], "broken generated internal references:\n" + "\n".join(errors))

    def test_validator_catches_routes_assets_and_fragments_without_fetching_external_urls(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok").mkdir()
            (root / "ok" / "index.html").write_text(
                '<main id="target"><a href="https://example.com/not-fetched">external</a></main>',
                encoding="utf-8",
            )
            (root / "index.html").write_text(
                """<!doctype html>
                <a href="/ok/#target">valid route and fragment</a>
                <a href="/missing/">missing route</a>
                <img src="/missing.png" alt="">
                <a href="#absent">missing fragment</a>
                """,
                encoding="utf-8",
            )

            errors = validate_internal_graph(root)

        self.assertEqual(
            errors,
            [
                "index.html: <a> href='/missing/' points to missing local target '/missing/'",
                "index.html: <img> src='/missing.png' points to missing local target '/missing.png'",
                "index.html: href='#absent' points to missing fragment #absent in index.html",
            ],
        )


if __name__ == "__main__":
    unittest.main()
