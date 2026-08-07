from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML_ROOT = ROOT / "html"
HASHED_ASSET = re.compile(r"\.[0-9a-f]{12}\.(?:css|mjs|json)$")


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    text: list[str] = field(default_factory=list)

    @property
    def accessible_text(self) -> str:
        return " ".join("".join(self.text).split())


class SemanticParser(HTMLParser):
    VOID = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[Element] = []
        self.elements: list[Element] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = {key: value or "" for key, value in attrs}
        element = Element(tag=tag, attrs=values)
        self.elements.append(element)
        if self.stack:
            self.stack[-1].text.append(" ")
        if tag not in self.VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            self.errors.append(f"unexpected closing tag </{tag}>")
            return
        if self.stack[-1].tag != tag:
            self.errors.append(
                f"closing tag </{tag}> does not match <{self.stack[-1].tag}>"
            )
            for index in range(len(self.stack) - 1, -1, -1):
                if self.stack[index].tag == tag:
                    del self.stack[index:]
                    return
            return
        completed = self.stack.pop()
        if self.stack:
            self.stack[-1].text.extend(completed.text)
            self.stack[-1].text.append(" ")

    def handle_data(self, data: str) -> None:
        if self.stack:
            self.stack[-1].text.append(data)

    def close(self) -> None:
        super().close()
        if self.stack:
            self.errors.append(
                "unclosed tags: " + ", ".join(row.tag for row in self.stack)
            )


def parse(path: Path) -> SemanticParser:
    parser = SemanticParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def local_target(source: Path, value: str) -> Path | None:
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https", "mailto", "tel"} or value.startswith("//"):
        return None
    if parsed.path == "" and parsed.fragment:
        return source
    path = unquote(parsed.path)
    if path in {"", "/"}:
        candidate = HTML_ROOT / "index.html"
    elif path.startswith("/"):
        candidate = HTML_ROOT / path.lstrip("/")
    else:
        candidate = source.parent / path
    candidate = candidate.resolve()
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


class HtmlSemanticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pages = sorted(HTML_ROOT.glob("*.html"))
        self.assertGreaterEqual(len(self.pages), 2)

    def test_pages_are_balanced_and_have_unique_ids(self) -> None:
        for path in self.pages:
            with self.subTest(page=path.name):
                parsed = parse(path)
                self.assertEqual(parsed.errors, [])
                ids = [
                    row.attrs["id"]
                    for row in parsed.elements
                    if row.attrs.get("id")
                ]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(
                    any(row.tag == "main" for row in parsed.elements),
                    "page must have a main landmark",
                )
                titles = [
                    row.accessible_text
                    for row in parsed.elements
                    if row.tag == "title"
                ]
                self.assertEqual(len(titles), 1)
                self.assertTrue(titles[0])
                roots = [row for row in parsed.elements if row.tag == "html"]
                self.assertEqual(len(roots), 1)
                self.assertTrue(roots[0].attrs.get("lang"))

    def test_fragment_and_file_links_resolve(self) -> None:
        for path in self.pages:
            parsed = parse(path)
            ids = {
                row.attrs["id"]
                for row in parsed.elements
                if row.attrs.get("id")
            }
            for row in parsed.elements:
                for attribute in ("href", "src"):
                    value = row.attrs.get(attribute)
                    if not value:
                        continue
                    with self.subTest(page=path.name, attribute=attribute, value=value):
                        split = urlsplit(value)
                        target = local_target(path, value)
                        if split.path == "" and split.fragment:
                            self.assertIn(split.fragment, ids)
                        if target is None:
                            continue
                        self.assertTrue(
                            target.is_relative_to(HTML_ROOT),
                            "local link must remain inside the public html tree",
                        )
                        self.assertTrue(target.is_file(), f"missing target: {target}")
                        if split.fragment and target.suffix == ".html":
                            target_ids = {
                                item.attrs["id"]
                                for item in parse(target).elements
                                if item.attrs.get("id")
                            }
                            self.assertIn(split.fragment, target_ids)

    def test_controls_and_images_have_accessible_names(self) -> None:
        for path in self.pages:
            parsed = parse(path)
            for row in parsed.elements:
                with self.subTest(page=path.name, tag=row.tag, id=row.attrs.get("id")):
                    if row.tag == "button":
                        self.assertTrue(
                            row.accessible_text
                            or row.attrs.get("aria-label")
                            or row.attrs.get("aria-labelledby")
                        )
                    if row.tag == "input" and row.attrs.get("type", "text") != "hidden":
                        self.assertTrue(
                            row.attrs.get("aria-label")
                            or row.attrs.get("aria-labelledby")
                            or row.attrs.get("title")
                        )
                    if row.tag == "img":
                        self.assertIn("alt", row.attrs)
                    for forbidden in ("onclick", "onkeydown", "onkeyup", "oninput"):
                        self.assertNotIn(forbidden, row.attrs)

    def test_cv_dialog_has_complete_modal_contract(self) -> None:
        parsed = parse(HTML_ROOT / "index.html")
        by_id = {
            row.attrs["id"]: row
            for row in parsed.elements
            if row.attrs.get("id")
        }
        dialog = by_id["chatDialog"]
        self.assertEqual(dialog.attrs.get("role"), "dialog")
        self.assertEqual(dialog.attrs.get("aria-modal"), "true")
        self.assertIn(dialog.attrs.get("aria-labelledby"), by_id)
        self.assertIn(dialog.attrs.get("aria-describedby"), by_id)
        self.assertEqual(by_id["chatStatus"].attrs.get("role"), "status")
        self.assertEqual(by_id["chatLog"].attrs.get("role"), "log")
        self.assertEqual(by_id["chatLog"].attrs.get("aria-live"), "polite")
        skip_links = [
            row
            for row in parsed.elements
            if row.tag == "a" and row.attrs.get("href") == "#main"
        ]
        self.assertEqual(len(skip_links), 1)

    def test_fingerprinted_assets_are_named_by_content(self) -> None:
        parsed = parse(HTML_ROOT / "index.html")
        values = []
        for row in parsed.elements:
            values.extend(
                value
                for value in (row.attrs.get("href"), row.attrs.get("src"))
                if value and HASHED_ASSET.search(urlsplit(value).path)
            )
        self.assertGreaterEqual(len(values), 2)
        for value in values:
            path = local_target(HTML_ROOT / "index.html", value)
            assert path is not None
            match = re.search(r"\.([0-9a-f]{12})\.", path.name)
            assert match is not None
            import hashlib

            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest()[:12],
                match.group(1),
            )


if __name__ == "__main__":
    unittest.main()
