from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

index = ROOT / "frontend/index.html"
text = index.read_text(encoding="utf-8")
for line in (
    '  <link rel="alternate" hreflang="en" href="https://rozkalns.net/en/">\n',
    '  <link rel="alternate" hreflang="de" href="https://rozkalns.net/de/">\n',
    '  <link rel="alternate" hreflang="lv" href="https://rozkalns.net/lv/">\n',
    '  <link rel="alternate" hreflang="x-default" href="https://rozkalns.net/en/">\n',
):
    if text.count(line) != 1:
        raise SystemExit(f"frontend/index.html: expected one temporary alternate line: {line!r}")
    text = text.replace(line, "", 1)
index.write_text(text, encoding="utf-8")

seo = ROOT / "tests/test_seo_canonical.py"
text = seo.read_text(encoding="utf-8")
old = '''            for language, href in ALTERNATES.items():
                marker = f'<link rel="alternate" hreflang="{language}" href="{href}">'
                self.assertEqual(html.count(marker), 1, f"{relative}: {marker}")
'''
if text.count(old) != 1:
    raise SystemExit("tests/test_seo_canonical.py: root alternate expectation missing")
text = text.replace(
    old,
    '''            self.assertNotIn('<link rel="alternate" hreflang=', html)
''',
    1,
)
seo.write_text(text, encoding="utf-8")
