#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "frontend" / "index.html"
COMPONENTS = ROOT / "frontend" / "styles" / "components.css"
RESPONSIVE = ROOT / "frontend" / "styles" / "responsive.css"


def require_once(text: str, needle: str, label: str) -> str:
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text


html = INDEX.read_text(encoding="utf-8")

focus_pattern = re.compile(r'\n      <div class="focus-tags">.*?</div>', re.S)
html, count = focus_pattern.subn("", html, count=1)
if count != 1:
    raise SystemExit(f"focus tags: expected one block, found {count}")

smart_action = re.compile(r'<a class="button" href="/smarthome\.html">.*?</a>', re.S)
html, count = smart_action.subn(
    '<a class=button href=//github.com/rozkalnsandris rel=me>GitHub ↗</a>',
    html,
    count=1,
)
if count != 1:
    raise SystemExit(f"smart-home hero action: expected one link, found {count}")

primary_pattern = re.compile(r'<article class="project-entry primary">.*?</article>', re.S)
primary = list(primary_pattern.finditer(html))
if len(primary) != 3:
    raise SystemExit(f"primary projects: expected 3, found {len(primary)}")

proof = (
    '<a class="tech-tag github-row" href=//github.com/rozkalnsandris/hermes-tech>GitHub</a>',
    '<a class="tech-tag github-row" href=//github.com/rozkalnsandris/RPi5_main>GitHub</a>',
    '<a class="tech-tag github-row" href=//github.com/rozkalnsandris/home-assistant-config>GitHub</a>'
    '<a class="tech-tag github-row" href=/smarthome.html><span data-i18n=smart_demo>Smart-home demo</span></a>',
)

pieces = []
last = 0
for match, insert in zip(primary, proof):
    article = match.group(0)
    tail = '</div></div></article>'
    require_once(article, tail, "primary project tail")
    article = article.replace(tail, insert + tail, 1)
    pieces.append(html[last:match.start()])
    pieces.append(article)
    last = match.end()
pieces.append(html[last:])
html = "".join(pieces)
INDEX.write_text(html, encoding="utf-8")

components = COMPONENTS.read_text(encoding="utf-8")
for dead_rule in (
    '.brand:hover { color: var(--accent); text-decoration: none; }\n',
    '.focus-tags { grid-area: focus; display: flex; flex-wrap: wrap; gap: 7px; margin-block-start: 2px; padding: 0; }\n',
    '.pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px solid var(--accent-line); border-radius: 999px; background: var(--surface); color: var(--accent-strong); font: 700 11px/1.35 var(--sans); }\n',
):
    require_once(components, dead_rule, "unused hero CSS")
    components = components.replace(dead_rule, "", 1)
COMPONENTS.write_text(components, encoding="utf-8")

responsive = RESPONSIVE.read_text(encoding="utf-8")
old_mobile = '''@media (max-width: 639px) {
  .hero-shell { gap: 9px 12px; padding-block: 14px; padding-inline: 14px; }
  .site-nav { gap: 2px; overflow: visible; }
  .site-nav a:nth-child(1), .site-nav a:nth-child(6) { display: none; }
  .site-nav a { min-width: 0; flex: 1 1 0; justify-content: center; padding-inline: 5px; font-size: 10.5px; }
  .focus-tags { display: none; }
  .contacts { padding: 10px 12px; }
  .profile-languages { gap: 5px; }
  .actions { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); width: 100%; }
  .actions .button { width: 100%; padding-inline: 10px; }
  .actions .chat-launcher-inline { grid-column: 1 / -1; width: 100%; }
}
'''
new_mobile = '''@media (max-width: 639px) {
  .hero-shell { gap: 9px 12px; padding: 14px; }
  .site-nav { gap: 2px; overflow: visible; }
  .site-nav a { min-width: 0; flex: 1; justify-content: center; padding-inline: 5px; font-size: 10.5px; }
  .site-nav a:first-child, .site-nav a:last-child { display: none; }
}
'''
require_once(responsive, old_mobile, "mobile polish block")
responsive = responsive.replace(old_mobile, new_mobile, 1)
wide_focus = '  .focus-tags { max-width: 52ch; }\n'
require_once(responsive, wide_focus, "wide focus rule")
responsive = responsive.replace(wide_focus, "", 1)
RESPONSIVE.write_text(responsive, encoding="utf-8")

print("UI_POLISH_312_APPLY=PASS")
