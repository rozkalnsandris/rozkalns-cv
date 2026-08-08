#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def replace_once(path_name: str, old: str, new: str) -> None:
    path = Path(path_name)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"C4_CUTOVER_ANCHOR_FAIL path={path_name} count={count} old={old!r}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


replace_once(
    "frontend/index.html",
    '  <link rel="stylesheet" href="./styles/main.css">\n'
    '  <link rel="stylesheet" href="./styles/extra.css">\n',
    '  <link rel="stylesheet" href="./styles/index.css">\n',
)
replace_once(
    "frontend/smarthome.html",
    '  <link rel="stylesheet" href="./styles/main.css">\n',
    '  <link rel="stylesheet" href="./styles/index.css">\n',
)

replace_once(
    "scripts/validate-source.sh",
    "    frontend/styles/main.css \\\n"
    "    frontend/styles/extra.css \\\n",
    "    frontend/styles/index.css \\\n"
    "    frontend/styles/tokens.css \\\n"
    "    frontend/styles/base.css \\\n"
    "    frontend/styles/layout.css \\\n"
    "    frontend/styles/components.css \\\n"
    "    frontend/styles/features/stats.css \\\n"
    "    frontend/styles/features/chat.css \\\n"
    "    frontend/styles/features/contact.css \\\n"
    "    frontend/styles/features/smarthome.css \\\n"
    "    frontend/styles/responsive.css \\\n"
    "    frontend/styles/print.css \\\n",
)
replace_once(
    "scripts/validate-source.sh",
    "for retired in update.sh update_cv-1.sh cloudflared.env.example; do",
    "for retired in update.sh update_cv-1.sh cloudflared.env.example frontend/styles/main.css frontend/styles/extra.css; do",
)

replace_once(
    "scripts/check-frontend-dist.mjs",
    '  "frontend/ui/icons.mjs"\n]) {',
    '  "frontend/ui/icons.mjs",\n'
    '  "frontend/styles/index.css",\n'
    '  "frontend/styles/tokens.css",\n'
    '  "frontend/styles/base.css",\n'
    '  "frontend/styles/layout.css",\n'
    '  "frontend/styles/components.css",\n'
    '  "frontend/styles/features/stats.css",\n'
    '  "frontend/styles/features/chat.css",\n'
    '  "frontend/styles/features/contact.css",\n'
    '  "frontend/styles/features/smarthome.css",\n'
    '  "frontend/styles/responsive.css",\n'
    '  "frontend/styles/print.css"\n]) {',
)

replace_once(
    "tests/test_contact_markup.py",
    '        self.assertIn(\'src="./enhancements.mjs"\', source)\n'
    '        self.assertIn(\'href="./styles/extra.css"\', source)\n',
    '        self.assertIn(\'src="./enhancements.mjs"\', source)\n'
    '        self.assertIn(\'href="./styles/index.css"\', source)\n'
    '        self.assertNotIn("styles/main.css", source)\n'
    '        self.assertNotIn("styles/extra.css", source)\n',
)
replace_once(
    "tests/test_contact_markup.py",
    '        self.assertGreaterEqual(len(entry.get("css", [])), 1)\n'
    '        for relative in [entry["file"], *entry.get("css", [])]:\n'
    '            self.assertRegex(relative, r"\\.[0-9a-f]{12}\\.(?:mjs|css)$")\n'
    '            self.assertTrue((ROOT / "html" / relative).is_file(), relative)\n',
    '        css_assets = sorted({\n'
    '            item\n'
    '            for row in manifest.values()\n'
    '            for item in row.get("css", [])\n'
    '        })\n'
    '        self.assertGreaterEqual(len(css_assets), 1)\n'
    '        for relative in [entry["file"], *css_assets]:\n'
    '            self.assertRegex(relative, r"\\.[0-9a-f]{12}\\.(?:mjs|css)$")\n'
    '            self.assertTrue((ROOT / "html" / relative).is_file(), relative)\n',
)
replace_once(
    "tests/test_contact_markup.py",
    '        css = (ROOT / "frontend" / "styles" / "extra.css").read_text(\n'
    '            encoding="utf-8"\n'
    '        )\n'
    '        self.assertIn(".skill-chip::before { content: none; }", css)\n'
    '        self.assertIn(".skill-chip svg", css)\n',
    '        css = (ROOT / "frontend" / "styles" / "components.css").read_text(\n'
    '            encoding="utf-8"\n'
    '        )\n'
    '        self.assertNotIn(".skill-chip::before", css)\n'
    '        self.assertIn(".skill-chip svg", css)\n',
)

replace_once(
    "tests/test_frontend_contract.py",
    'SOURCE_CSS = ROOT / "frontend" / "styles" / "main.css"\n',
    'SOURCE_LAYOUT = ROOT / "frontend" / "styles" / "layout.css"\n'
    'SOURCE_RESPONSIVE = ROOT / "frontend" / "styles" / "responsive.css"\n',
)
replace_once(
    "tests/test_frontend_contract.py",
    "        self.assertGreaterEqual(len(assets), 8)\n",
    "        self.assertGreaterEqual(len(assets), 7)\n"
    '        self.assertGreaterEqual(sum(path.endswith(".css") for path in assets), 1)\n'
    '        self.assertGreaterEqual(sum(path.endswith((".mjs", ".js")) for path in assets), 3)\n',
)
replace_once(
    "tests/test_frontend_contract.py",
    '        css = SOURCE_CSS.read_text(encoding="utf-8")\n',
    '        layout = SOURCE_LAYOUT.read_text(encoding="utf-8")\n'
    '        responsive = SOURCE_RESPONSIVE.read_text(encoding="utf-8")\n',
)
replace_once(
    "tests/test_frontend_contract.py",
    "        self.assertIn('@media (max-width: 760px)', css)\n"
    "        self.assertNotIn('@media (max-width: 850px)', css)\n"
    "        self.assertIn('grid-template-columns: 340px minmax(0,1fr)', css)\n",
    "        self.assertIn('@media (max-width: 760px)', responsive)\n"
    "        self.assertNotIn('@media (max-width: 850px)', responsive)\n"
    "        self.assertIn('grid-template-columns: 340px minmax(0,1fr)', layout)\n",
)

for retired in (
    Path("frontend/styles/main.css"),
    Path("frontend/styles/extra.css"),
):
    if not retired.is_file():
        raise SystemExit(f"C4_RETIRED_SOURCE_MISSING_BEFORE_CUTOVER={retired}")
    retired.unlink()

print("C4_SOURCE_CUTOVER=PASS")
