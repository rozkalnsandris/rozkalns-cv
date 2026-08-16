from pathlib import Path
import re

# Integrate GitHub proof into the existing Skills definition list.
index = Path("frontend/index.html")
text = index.read_text(encoding="utf-8")
pattern = re.compile(
    r'      <div class="work-rail">\n'
    r'      <section id="skills">(?P<skills>[\s\S]*?)</section>\n'
    r'      <section id="github-projects"><h2 class=org>GitHub <span data-i18n=projects_title>Projects</span></h2>(?P<github>[\s\S]*?)</section>\n'
    r'      </div>'
)
match = pattern.search(text)
if not match or len(pattern.findall(text)) != 1:
    raise SystemExit("expected exactly one Skills/work-rail/GitHub structure")
skills = match.group("skills")
github = match.group("github")
if not skills.endswith("</dl>"):
    raise SystemExit("Skills section must end with definition list")
skills = skills[:-5] + (
    '<div class=skill-row id=github-projects>'
    '<dt>GitHub <span data-i18n=projects_title>Projects</span></dt>'
    f'<dd>{github}</dd></div></dl>'
)
replacement = f'      <section id="skills">{skills}</section>'
text = pattern.sub(replacement, text, count=1)
index.write_text(text, encoding="utf-8")

# Remove the now-unnecessary wrapper rules and make #skills the rail grid item.
layout = Path("frontend/styles/layout.css")
text = layout.read_text(encoding="utf-8")
old = ".work-rail { display: contents; }\n"
if text.count(old) != 1:
    raise SystemExit("expected one mobile work-rail rule")
layout.write_text(text.replace(old, ""), encoding="utf-8")

responsive = Path("frontend/styles/responsive.css")
text = responsive.read_text(encoding="utf-8")
replacements = {
    "  .work-rail { grid-area: rail; display: grid; gap: 28px; }": "  #skills { grid-area: rail; }",
    "  .work-rail .section-heading, #experience .section-heading { margin-block-end: 14px; }": "  #skills .section-heading, #experience .section-heading { margin-block-end: 14px; }",
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f"expected one responsive contract: {old}")
    text = text.replace(old, new)
responsive.write_text(text, encoding="utf-8")

# Update Python structure contract.
contract = Path("tests/test_github_project_links.py")
text = contract.read_text(encoding="utf-8")
text = text.replace(
    "        self.assertIn('<section id=\"github-projects\">', INDEX)",
    "        self.assertIn('<div class=skill-row id=github-projects>', INDEX)\n        self.assertNotIn('<section id=\"github-projects\">', INDEX)",
)
text = text.replace(
    "        self.assertIn('<h2 class=org>GitHub <span data-i18n=projects_title>Projects</span></h2>', INDEX)",
    "        self.assertIn('<dt>GitHub <span data-i18n=projects_title>Projects</span></dt>', INDEX)",
)
contract.write_text(text, encoding="utf-8")

# Update Node source contracts for the integrated row.
frontend_test = Path("tests/frontend.test.mjs")
text = frontend_test.read_text(encoding="utf-8")
old_match = '  const section = source.match(/<section id="github-projects">([\\s\\S]*?)<\\/section>/)?.[1] || "";'
new_match = '  const proof = source.match(/<div class=skill-row id=github-projects>([\\s\\S]*?)<\\/div><\\/dl>/)?.[1] || "";'
if text.count(old_match) != 2:
    raise SystemExit(f"expected two GitHub section source contracts, got {text.count(old_match)}")
text = text.replace(old_match, new_match)
old_featured = '  const featured = section.match(/<div class=skill-list>([\\s\\S]*?)<\\/div>/)?.[1] || "";'
new_featured = '  const featured = proof.match(/<dd><div class=skill-list>([\\s\\S]*?)<\\/div><details/)?.[1] || "";'
if text.count(old_featured) != 1:
    raise SystemExit("expected one featured GitHub list contract")
text = text.replace(old_featured, new_featured)
text = text.replace("section.match", "proof.match").replace("section.includes", "proof.includes")
frontend_test.write_text(text, encoding="utf-8")

# Update real Chromium geometry/semantics contracts.
browser = Path("tests/browser-smoke.mjs")
text = browser.read_text(encoding="utf-8")
replacements = {
    "selected: [...document.querySelectorAll('#github-projects > .skill-list a')].map((link) => link.textContent.trim()),": "selected: [...document.querySelectorAll('#github-projects > dd > .skill-list a')].map((link) => link.textContent.trim()),",
    "rowSizes: [...document.querySelectorAll('#github-projects > .skill-list .github-row')].map((row) => {": "rowSizes: [...document.querySelectorAll('#github-projects > dd > .skill-list .github-row')].map((row) => {",
    "skillBottom: document.querySelector('#skills')?.getBoundingClientRect().bottom,\n          githubTop: document.querySelector('#github-projects')?.getBoundingClientRect().top": "proofParent: document.querySelector('#github-projects')?.closest('section')?.id,\n          proofTag: document.querySelector('#github-projects')?.tagName",
    "const proofHeading = document.querySelector('#github-projects h2');": "const proofHeading = document.querySelector('#github-projects > dt');",
    "const firstRow = document.querySelector('#github-projects > .skill-list .github-row');": "const firstRow = document.querySelector('#github-projects > dd > .skill-list .github-row');",
    "const summary = document.querySelector('#github-projects > details > summary');": "const summary = document.querySelector('#github-projects > dd > details > summary');",
    "        if (viewport.width >= 900) {\n          const railGap = githubProof.githubTop - githubProof.skillBottom;\n          assert.ok(railGap >= 20 && railGap <= 36, `responsive ${viewport.width}px ${locale.label} Skills/GitHub rail gap: ${railGap}`);\n        }": "        assert.equal(githubProof.proofParent, 'skills', `responsive ${viewport.width}px ${locale.label} GitHub proof parent`);\n        assert.equal(githubProof.proofTag, 'DIV', `responsive ${viewport.width}px ${locale.label} GitHub proof row tag`);",
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f"expected one Chromium contract: {old[:80]!r}; got {text.count(old)}")
    text = text.replace(old, new)
browser.write_text(text, encoding="utf-8")
