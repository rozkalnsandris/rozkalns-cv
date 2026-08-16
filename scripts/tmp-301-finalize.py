from pathlib import Path

p = Path('frontend/index.html')
s = p.read_text()
old = '      <section id="skills">'
new = '      <div class="work-rail">\n      <section id="skills">'
assert s.count(old) == 1
s = s.replace(old, new, 1)
old = '</div></details></section>\n\n      <section id="experience">'
new = '</div></details></section>\n      </div>\n\n      <section id="experience">'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))

p = Path('frontend/styles/layout.css')
s = p.read_text()
old = '.work-layout { min-width: 0; display: grid; gap: clamp(24px,4vw,42px); }'
new = old + '\n.work-rail { display: contents; }'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))

p = Path('frontend/styles/responsive.css')
s = p.read_text()
old = '''  .work-layout { grid-template-columns: minmax(0,1.55fr) minmax(280px,.78fr); grid-template-areas: "projects skills" "projects github" "experience experience"; gap: clamp(30px,4vw,46px) clamp(30px,4vw,52px); align-items: start; }
  #projects { grid-area: projects; }
  #skills { grid-area: skills; }
  #github-projects { grid-area: github; }
  #experience { grid-area: experience; }
  #skills .section-heading, #experience .section-heading { margin-block-end: 14px; }'''
new = '''  .work-layout { grid-template-columns: minmax(0,1.55fr) minmax(280px,.78fr); grid-template-areas: "projects rail" "experience experience"; gap: clamp(30px,4vw,46px) clamp(30px,4vw,52px); align-items: start; }
  #projects { grid-area: projects; }
  .work-rail { grid-area: rail; display: grid; gap: 28px; }
  #experience { grid-area: experience; }
  .work-rail .section-heading, #experience .section-heading { margin-block-end: 14px; }'''
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))

p = Path('tests/test_css_source_contract.py')
s = p.read_text()
s = s.replace("self.assertIn('grid-template-areas: \"projects skills\" \"projects github\" \"experience experience\";', responsive)", "self.assertIn('grid-template-areas: \"projects rail\" \"experience experience\";', responsive)")
s = s.replace('self.assertIn("#github-projects { grid-area: github; }", responsive)', 'self.assertIn(".work-rail { grid-area: rail; display: grid; gap: 28px; }", responsive)')
p.write_text(s)

p = Path('tests/test_frontend_contract.py')
s = p.read_text()
s = s.replace("self.assertIn('grid-template-areas: \"projects skills\" \"projects github\" \"experience experience\";', responsive)", "self.assertIn('grid-template-areas: \"projects rail\" \"experience experience\";', responsive)")
s = s.replace('self.assertIn("#github-projects { grid-area: github; }", responsive)', 'self.assertIn(".work-rail { grid-area: rail; display: grid; gap: 28px; }", responsive)')
anchor = "        self.assertIn('class=\"work-layout\"', html)\n"
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + "        self.assertIn('class=\"work-rail\"', html)\n        self.assertIn('.work-rail { display: contents; }', layout)\n", 1)
p.write_text(s)

p = Path('tests/browser-smoke.mjs')
s = p.read_text()
old = '''          rowSizes: [...document.querySelectorAll('#github-projects > .skill-list .github-row')].map((row) => {
            const rect = row.getBoundingClientRect();
            return { width: rect.width, height: rect.height };
          })'''
new = '''          rowSizes: [...document.querySelectorAll('#github-projects > .skill-list .github-row')].map((row) => {
            const rect = row.getBoundingClientRect();
            return { width: rect.width, height: rect.height };
          }),
          skillBottom: document.querySelector('#skills')?.getBoundingClientRect().bottom,
          githubTop: document.querySelector('#github-projects')?.getBoundingClientRect().top'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
anchor = '''        assert.ok(
          githubProof.rowSizes.every(({ width, height }) => width >= 120 && height >= 28 && height <= 34),
          `responsive ${viewport.width}px ${locale.label} GitHub rows must stay compact: ${JSON.stringify(githubProof.rowSizes)}`
        );'''
addition = anchor + '''
        if (viewport.width >= 900) {
          const railGap = githubProof.githubTop - githubProof.skillBottom;
          assert.ok(railGap >= 20 && railGap <= 36, `responsive ${viewport.width}px ${locale.label} Skills/GitHub rail gap: ${railGap}`);
        }'''
assert s.count(anchor) == 1
p.write_text(s.replace(anchor, addition, 1))
