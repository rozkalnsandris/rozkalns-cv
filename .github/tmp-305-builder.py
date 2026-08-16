from pathlib import Path

index = Path("frontend/index.html")
text = index.read_text(encoding="utf-8")
for old, new in {
    '<h2 class=org>SELECTED GITHUB PROJECTS</h2>': '<h2 class=org>GitHub <span data-i18n=projects_title>Projects</span></h2>',
    '<summary class="tech-tag">+ 4 more projects</summary>': '<summary class="tech-tag">+ 4 <span data-i18n=projects_title>Projects</span></summary>',
}.items():
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one HTML contract: {old!r}")
    text = text.replace(old, new)
index.write_text(text, encoding="utf-8")

contract = Path("tests/test_github_project_links.py")
text = contract.read_text(encoding="utf-8")
old = '        self.assertIn(\'<summary class="tech-tag">+ 4 more projects</summary>\', INDEX)'
new = "\n".join([
    '        self.assertIn(\'<h2 class=org>GitHub <span data-i18n=projects_title>Projects</span></h2>\', INDEX)',
    '        self.assertIn(\'<summary class="tech-tag">+ 4 <span data-i18n=projects_title>Projects</span></summary>\', INDEX)',
])
if text.count(old) != 1:
    raise SystemExit("expected one GitHub disclosure unit-test contract")
contract.write_text(text.replace(old, new), encoding="utf-8")

frontend_tests = Path("tests/frontend.test.mjs")
text = frontend_tests.read_text(encoding="utf-8")
old = 'assert.match(section, /<details class=project-list><summary class="tech-tag">\\+ 4 more projects<\\/summary><div class=skill-list>/);'
new = 'assert.match(section, /<details class=project-list><summary class="tech-tag">\\+ 4 <span data-i18n=projects_title>Projects<\\/span><\\/summary><div class=skill-list>/);'
if text.count(old) != 2:
    raise SystemExit(f"expected two stale frontend disclosure contracts, found {text.count(old)}")
frontend_tests.write_text(text.replace(old, new), encoding="utf-8")

browser = Path("tests/browser-smoke.mjs")
text = browser.read_text(encoding="utf-8")
old = """        assert.equal(proofHierarchy.proofText, 'SELECTED GITHUB PROJECTS');
        assert.equal(proofHierarchy.summaryText, '+ 4 more projects');"""
new = """        const proofLabels = {
          en: { heading: 'GitHub Projects', summary: '+ 4 Projects' },
          de: { heading: 'GitHub Projekte', summary: '+ 4 Projekte' },
          lv: { heading: 'GitHub Projekti', summary: '+ 4 Projekti' }
        }[locale.language];
        assert.equal(proofHierarchy.proofText, proofLabels.heading);
        assert.equal(proofHierarchy.summaryText, proofLabels.summary);"""
if text.count(old) != 1:
    raise SystemExit("expected one Chromium GitHub proof label contract")
browser.write_text(text.replace(old, new), encoding="utf-8")
