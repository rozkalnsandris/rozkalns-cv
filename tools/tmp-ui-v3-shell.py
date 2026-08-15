from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

index_path = ROOT / "frontend" / "index.html"
layout_path = ROOT / "frontend" / "styles" / "layout.css"
components_path = ROOT / "frontend" / "styles" / "components.css"
responsive_path = ROOT / "frontend" / "styles" / "responsive.css"
test_path = ROOT / "tests" / "test_frontend_contract.py"

html = index_path.read_text(encoding="utf-8")

nav_match = re.search(r"\n      <nav class=\"site-nav\" aria-label=\"CV\">[\s\S]*?\n      </nav>\n", html)
if not nav_match:
    raise SystemExit("site nav block not found")
nav = nav_match.group(0).strip("\n")
html = html[: nav_match.start()] + "\n" + html[nav_match.end() :]

old_header = '<header class="sidebar">'
new_header = '<header class="site-header hero-shell">'
if html.count(old_header) != 1:
    raise SystemExit("unexpected legacy header count")
html = html.replace(old_header, new_header, 1)

marker = new_header + "\n"
brand_and_nav = (
    '      <a class="brand" href="./" aria-label="Andris Rožkalns">AR</a>\n'
    + nav
    + "\n\n"
)
if marker not in html:
    raise SystemExit("new header marker missing")
html = html.replace(marker, marker + brand_and_nav, 1)

if '<main id="main">' not in html:
    raise SystemExit("main marker missing")
html = html.replace('<main id="main">', '<main id="main" class="v3-main">', 1)

section_classes = {
    "about": "v3-section v3-about",
    "projects": "v3-section v3-projects",
    "skills": "v3-section v3-skills",
    "experience": "v3-section v3-experience",
    "stats": "v3-section v3-stats",
    "education": "v3-section v3-education",
}
for section_id, classes in section_classes.items():
    old = f'<section id="{section_id}">'
    new = f'<section id="{section_id}" class="{classes}">'
    if html.count(old) != 1:
        raise SystemExit(f"unexpected section marker count: {section_id}")
    html = html.replace(old, new, 1)

index_path.write_text(html, encoding="utf-8")

layout_path.write_text(
    """.page {
  width: min(calc(100% - 24px), var(--maxw));
  margin-inline: auto;
  padding-block: 12px 72px;
}
.hero-shell {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  display: grid;
  grid-template-columns: 84px minmax(0,1fr);
  grid-template-areas:
    "brand lang"
    "nav nav"
    "photo name"
    "photo role"
    "tagline tagline"
    "contacts contacts"
    "focus focus"
    "langs langs"
    "actions actions"
    "verify verify";
  gap: 12px 14px;
  align-items: start;
  padding-block: 18px;
  padding-inline: 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  background: linear-gradient(145deg,var(--surface),var(--surface-2));
  box-shadow: var(--shadow-md);
}
.hero-shell::before {
  content: "";
  position: absolute;
  z-index: -1;
  inset-block-start: -86px;
  inset-inline-end: -74px;
  width: 210px;
  height: 210px;
  border-radius: 50%;
  background: var(--accent-soft);
}
.v3-main {
  min-width: 0;
  display: grid;
  gap: var(--section-gap);
  margin-block-start: 30px;
}
.v3-section { min-width: 0; }
section { margin: 0; scroll-margin-top: 118px; }
.section-heading {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-block-end: 20px;
}
.section-heading h2 {
  margin: 0;
  color: var(--text);
  font: 700 clamp(24px,6vw,34px)/1.05 var(--serif);
  letter-spacing: -.025em;
}
.section-heading::after {
  content: "";
  height: 1px;
  flex: 1;
  background: var(--border);
}
.lead {
  max-width: 70ch;
  margin: 0;
  color: var(--text-dim);
  font-size: 16px;
  line-height: 1.75;
}
.lead + .lead { margin-block-start: 12px; }
#about { padding-block: 2px; padding-inline: 4px; }
""",
    encoding="utf-8",
)

components = components_path.read_text(encoding="utf-8")
components = components.replace(".sidebar h1", ".hero-shell h1")

language_marker = ".language-switcher { grid-area: lang;"
if language_marker not in components:
    raise SystemExit("language switcher marker missing")
components = components.replace(
    language_marker,
    '.brand { grid-area: brand; align-self: center; color: var(--accent-strong); font: 800 22px/1 var(--serif); letter-spacing: -.04em; text-decoration: none; }\n.brand:hover { color: var(--accent); text-decoration: none; }\n' + language_marker,
    1,
)

old_role = ".role { grid-area: role; width: fit-content; margin: 0; padding: 7px 11px; border-radius: 999px; background: var(--accent-soft); color: var(--accent-strong); font-weight: 750; font-size: 13px; line-height: 1.2; }"
new_role = ".role { grid-area: role; width: fit-content; margin: 0; color: var(--accent-strong); font-weight: 800; font-size: 14px; line-height: 1.3; }"
if old_role not in components:
    raise SystemExit("role block missing")
components = components.replace(old_role, new_role, 1)

old_focus = ".focus-tags { grid-area: focus; display: flex; flex-wrap: wrap; gap: 7px; margin-top: 2px; padding: 12px 14px; border: 1px solid var(--accent-line); border-left: 3px solid var(--accent); border-radius: var(--radius-md); background: var(--accent-soft); }"
new_focus = ".focus-tags { grid-area: focus; display: flex; flex-wrap: wrap; gap: 7px; margin-block-start: 2px; padding: 0; }"
if old_focus not in components:
    raise SystemExit("focus block missing")
components = components.replace(old_focus, new_focus, 1)

old_languages = ".profile-languages { grid-area: langs; display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 0; padding: 12px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface); box-shadow: var(--shadow-sm); }"
new_languages = ".profile-languages { grid-area: langs; display: flex; flex-wrap: wrap; gap: 7px; margin: 0; padding: 0; }"
if old_languages not in components:
    raise SystemExit("profile languages block missing")
components = components.replace(old_languages, new_languages, 1)

components_path.write_text(components, encoding="utf-8")

responsive_path.write_text(
    """@media (min-width: 640px) {
  .page { width: min(calc(100% - 40px),var(--maxw)); padding-block-start: 20px; }
  .hero-shell { grid-template-columns: 116px minmax(0,1fr); padding-block: 22px; padding-inline: 22px; gap: 13px 18px; }
  .profile-photo { width: 116px; height: 146px; }
  .project-list { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .skill-row { grid-template-columns: 145px minmax(0,1fr); gap: 18px; }
  .education-row { grid-template-columns: 135px minmax(0,1fr); gap: 18px; }
  .entry { grid-template-columns: 145px minmax(0,1fr); gap: 18px; }
  .demo-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .stats-grid { grid-template-columns: repeat(4,minmax(0,1fr)); }
  .stat { border-right: 1px solid var(--border-soft); border-bottom: 1px solid var(--border-soft); }
  .stat:nth-child(2n) { border-right: 1px solid var(--border-soft); }
  .stat:nth-child(4n) { border-right: 0; }
  .stat:nth-last-child(-n+4) { border-bottom: 0; }
}
@media (min-width: 720px) {
  .actions { align-items: center; }
  .contact-reveal { width: fit-content; }
  .turnstile-mount { width: 300px; }
  .chat-launcher { right: 22px; bottom: 22px; }
  .dialog-backdrop { padding: 22px; }
}
@media (min-width: 900px) {
  .page { padding-block: 28px 84px; }
  .hero-shell {
    grid-template-columns: auto minmax(0,1fr) 260px;
    grid-template-areas:
      "brand nav lang"
      "name name photo"
      "role role photo"
      "tagline tagline photo"
      "contacts contacts photo"
      "focus focus photo"
      "langs langs photo"
      "actions actions photo"
      "verify verify photo";
    gap: 11px 28px;
    padding-block: 24px 26px;
    padding-inline: 26px;
    align-items: start;
  }
  .hero-shell::before { width: 320px; height: 320px; inset-block-start: -156px; inset-inline-end: -90px; }
  .brand { align-self: center; font-size: 24px; }
  .site-nav { align-self: center; justify-content: center; overflow: visible; }
  .site-nav a { min-height: 46px; padding-inline: 13px; }
  .language-switcher { align-self: center; }
  .profile-photo { width: 100%; height: 100%; min-height: 300px; max-height: 360px; border-radius: 24px; }
  .hero-shell h1 { align-self: end; max-width: 12ch; font-size: clamp(56px,5.2vw,74px); }
  .role { margin-block-start: 1px; font-size: 15px; }
  .tagline { max-width: 48ch; margin-block-start: 7px; font-size: 18px; line-height: 1.62; }
  .contacts { align-self: start; display: flex; flex-wrap: wrap; gap: 4px 18px; padding: 0; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
  .contact-row { min-height: 34px; }
  .focus-tags { max-width: 52ch; align-self: start; }
  .profile-languages { align-self: start; margin: 0; }
  .profile-language { width: auto; border-radius: 999px; }
  .contact-verify { align-self: start; }
  .actions { align-self: start; }
  .v3-main { margin-block-start: 44px; }
  #about { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 28px; padding-block: 4px; padding-inline: 18px; }
  #about .section-heading { grid-column: 1 / -1; margin-block-end: -2px; }
  #about .lead + .lead { margin-block-start: 0; }
  #projects .section-heading, #skills .section-heading, #experience .section-heading { margin-block-end: 24px; }
  .project-entry { min-height: 210px; padding: 22px; }
  .skill-list { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .skill-row { grid-template-columns: 1fr; align-content: start; padding: 20px; }
  .timeline { gap: 16px; }
  .entry { grid-template-columns: 160px minmax(0,1fr); padding: 22px; }
}
""",
    encoding="utf-8",
)

tests = test_path.read_text(encoding="utf-8")
old_assertions = """        self.assertIn('grid-template-columns: 84px minmax(0,1fr)', layout)\n        self.assertIn('\"photo name\"', layout)\n        self.assertIn('grid-template-columns: minmax(0,1.25fr) 220px minmax(260px,.9fr)', responsive)\n        self.assertIn('\"name photo contacts\"', responsive)\n"""
new_assertions = """        self.assertIn('class=\"site-header hero-shell\"', html)\n        self.assertIn('class=\"brand\"', html)\n        self.assertLess(html.index('class=\"brand\"'), html.index('class=\"site-nav\"'))\n        self.assertLess(html.index('class=\"site-nav\"'), html.index('class=\"language-switcher\"'))\n        self.assertIn('\"brand lang\"', layout)\n        self.assertIn('\"photo name\"', layout)\n        self.assertIn('padding-inline: 18px', layout)\n        self.assertIn('grid-template-columns: auto minmax(0,1fr) 260px;', responsive)\n        self.assertIn('\"brand nav lang\"', responsive)\n        self.assertIn('\"name name photo\"', responsive)\n"""
if old_assertions not in tests:
    raise SystemExit("legacy layout assertions not found")
tests = tests.replace(old_assertions, new_assertions, 1)
test_path.write_text(tests, encoding="utf-8")

print("UI_V3_SHELL_PATCH=PASS")
