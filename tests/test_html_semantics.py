from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
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
            label_targets = {
                row.attrs["for"]
                for row in parsed.elements
                if row.tag == "label" and row.attrs.get("for") and row.accessible_text
            }
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
                            or row.attrs.get("id") in label_targets
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
        self.assertEqual(by_id["chatLog"].attrs.get("aria-relevant"), "additions")
        self.assertEqual(by_id["chatLog"].attrs.get("aria-atomic"), "false")
        self.assertEqual(by_id["chatStatus"].attrs.get("aria-live"), "polite")
        skip_links = [
            row
            for row in parsed.elements
            if row.tag == "a" and row.attrs.get("href") == "#main"
        ]
        self.assertEqual(len(skip_links), 1)

    def test_language_switchers_are_named_toggle_groups(self) -> None:
        expected_labels = {"en": "English", "de": "Deutsch", "lv": "Latviešu"}
        for path in self.pages:
            parsed = parse(path)
            switchers = [
                row
                for row in parsed.elements
                if "language-switcher" in row.attrs.get("class", "").split()
            ]
            self.assertEqual(len(switchers), 1, path.name)
            switcher = switchers[0]
            self.assertEqual(switcher.attrs.get("role"), "group")
            self.assertEqual(switcher.attrs.get("aria-label"), "Language")
            buttons = [row for row in parsed.elements if row.attrs.get("data-lang")]
            self.assertEqual({row.attrs.get("data-lang") for row in buttons}, set(expected_labels))
            self.assertEqual(
                {row.attrs.get("data-lang"): row.attrs.get("aria-label") for row in buttons},
                expected_labels,
            )
            pressed = [row for row in buttons if row.attrs.get("aria-pressed") == "true"]
            self.assertEqual(len(pressed), 1)
            self.assertTrue(all(row.attrs.get("aria-pressed") in {"true", "false"} for row in buttons))

    def test_smarthome_heading_hierarchy(self) -> None:
        parsed = parse(HTML_ROOT / "smarthome.html")
        h1 = [row for row in parsed.elements if row.tag == "h1"]
        h2 = [row for row in parsed.elements if row.tag == "h2"]
        h3 = [row for row in parsed.elements if row.tag == "h3"]
        self.assertEqual(len(h1), 1)
        self.assertEqual([row.accessible_text for row in h2], ["Climate", "Devices"])
        self.assertEqual(len(h3), 8)

    def test_fingerprinted_assets_are_manifest_owned(self) -> None:
        manifest = json.loads(
            (ROOT / "frontend-dist-manifest.json").read_text(encoding="utf-8")
        )
        manifest_assets: set[str] = set()
        for row in manifest.values():
            if isinstance(row.get("file"), str):
                manifest_assets.add(row["file"])
            for key in ("css", "assets"):
                manifest_assets.update(row.get(key, []))

        values: list[str] = []
        for page in self.pages:
            parsed = parse(page)
            for row in parsed.elements:
                values.extend(
                    value
                    for value in (row.attrs.get("href"), row.attrs.get("src"))
                    if value and HASHED_ASSET.search(urlsplit(value).path)
                )
        self.assertGreaterEqual(len(values), 4)
        for value in values:
            relative = urlsplit(value).path.lstrip("/")
            self.assertRegex(relative, HASHED_ASSET)
            self.assertIn(relative, manifest_assets)
            self.assertTrue((HTML_ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
