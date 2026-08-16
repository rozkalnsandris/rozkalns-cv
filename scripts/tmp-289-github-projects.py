from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

index_path = ROOT / "frontend" / "index.html"
index = index_path.read_text(encoding="utf-8")
index_marker = '        </div>\n      </section>\n\n      <section id="skills">'
assert index.count(index_marker) == 1, "projects/skills marker changed"
index = index.replace(
    index_marker,
    '        </div>\n        <div id="githubProjects"></div>\n      </section>\n\n      <section id="skills">',
)
index_path.write_text(index, encoding="utf-8")

app_path = ROOT / "frontend" / "app.mjs"
app = app_path.read_text(encoding="utf-8")
app_marker = 'const PDFS = Object.freeze({\n  en: "/cv.pdf",\n  de: "/cv-de.pdf",\n  lv: "/cv-lv.pdf"\n});\n'
assert app.count(app_marker) == 1, "PDF map marker changed"
app_insert = app_marker + '''\nconst GITHUB_PROJECTS = `<a class="tech-tag" href="https://github.com/rozkalnsandris/hermes-tech">GH · hermes-tech</a><a class="tech-tag" href="https://github.com/rozkalnsandris/RPi5_main">GH · RPi5_main</a><a class="tech-tag" href="https://github.com/rozkalnsandris/hermes-deals">GH · hermes-deals</a><a class="tech-tag" href="https://github.com/rozkalnsandris/rozkalns-control-center">GH · rozkalns-control-center</a><a class="tech-tag" href="https://github.com/rozkalnsandris">GitHub ↗</a>`;\n\nfunction renderGitHubProjects() {\n  const mount = document.querySelector("#githubProjects");\n  if (!mount) return;\n  mount.className = "tech-tags";\n  mount.setAttribute("aria-label", "GitHub");\n  mount.innerHTML = GITHUB_PROJECTS;\n}\n'''
app = app.replace(app_marker, app_insert)
init_marker = 'async function init() {\n  enhanceSkillIcons();\n'
assert app.count(init_marker) == 1, "init marker changed"
app = app.replace(init_marker, 'async function init() {\n  enhanceSkillIcons();\n  renderGitHubProjects();\n')
app_path.write_text(app, encoding="utf-8")

css_path = ROOT / "frontend" / "styles" / "components.css"
css = css_path.read_text(encoding="utf-8")
css_marker = '.tech-tag { display: inline-flex; align-items: center; gap: 6px; min-height: 30px; padding: 5px 9px; border: 1px solid var(--border-soft); border-radius: 999px; background: var(--surface-2); color: var(--text-dim); font: 650 11px/1.35 var(--sans); }\n'
assert css.count(css_marker) == 1, "tech-tag marker changed"
css = css.replace(css_marker, css_marker + '.tech-tag:is(a) { text-decoration: none; }\n')
css_path.write_text(css, encoding="utf-8")

browser_path = ROOT / "tests" / "browser-smoke.mjs"
browser = browser_path.read_text(encoding="utf-8")
browser_marker = '''        await cdp.waitFor(\n          `["rail", "inline"].includes(document.querySelector('#chatLauncher')?.dataset.placement)`,\n          10_000,\n          `responsive ${viewport.width}px ${locale.label} launcher placement`\n        );\n        const layout = await cdp.evaluate(`(() => {\n'''
assert browser.count(browser_marker) == 1, "responsive launcher marker changed"
browser = browser.replace(
    browser_marker,
    '''        await cdp.waitFor(\n          `["rail", "inline"].includes(document.querySelector('#chatLauncher')?.dataset.placement)`,\n          10_000,\n          `responsive ${viewport.width}px ${locale.label} launcher placement`\n        );\n        assert.equal(\n          await cdp.evaluate(`document.querySelectorAll('#githubProjects a').length`),\n          5,\n          `responsive ${viewport.width}px ${locale.label} GitHub shelf`\n        );\n        const layout = await cdp.evaluate(`(() => {\n''',
)
browser_path.write_text(browser, encoding="utf-8")

test_path = ROOT / "tests" / "test_github_project_links.py"
test_path.write_text('''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nINDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")\nAPP = (ROOT / "frontend" / "app.mjs").read_text(encoding="utf-8")\n\n\nclass GitHubProjectLinksTest(unittest.TestCase):\n    def test_compact_public_repo_allowlist(self) -> None:\n        self.assertIn('id="githubProjects"', INDEX)\n        for repo in ("hermes-tech", "RPi5_main", "hermes-deals", "rozkalns-control-center"):\n            self.assertIn(f"/{repo}\", APP)\n        self.assertNotIn("api.github.com", APP)\n        self.assertNotIn("YouTube_Marcim", APP)\n        self.assertNotIn("hermes-email-skill", APP)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")
