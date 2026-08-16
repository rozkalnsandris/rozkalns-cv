from pathlib import Path


def patch_index() -> None:
    path = Path("frontend/index.html")
    text = path.read_text(encoding="utf-8")
    old_hero = "<a href=https://github.com/rozkalnsandris rel=me>GitHub · hermes-tech · RPi5_main · hermes-deals · control-center</a>"
    if old_hero in text:
        text = text.replace(old_hero, "<a href=https://github.com/rozkalnsandris rel=me>GitHub</a>", 1)

    if 'id="github-projects"' not in text:
        marker = '      <section id="experience">'
        if text.count(marker) != 1:
            raise SystemExit("experience insertion marker mismatch")
        block = '''      <section id="github-projects">
        <div class="section-heading"><h2>GitHub</h2></div>
        <div class="skill-list">
          <div class="skill-row"><div class="skill-chips"><a class=skill-chip href=https://github.com/rozkalnsandris/hermes-tech>hermes-tech</a><a class=skill-chip href=https://github.com/rozkalnsandris/RPi5_main>RPi5_main</a><a class=skill-chip href=https://github.com/rozkalnsandris/hermes-deals>hermes-deals</a><a class=skill-chip href=https://github.com/rozkalnsandris/rozkalns-control-center>rozkalns-control-center</a><a class=skill-chip href=https://github.com/rozkalnsandris/dashboard_RPi5>dashboard_RPi5</a></div></div>
          <details class="skill-row"><summary class=org aria-label="4 more GitHub projects">+ 4</summary><div class="skill-chips"><a class=skill-chip href=https://github.com/rozkalnsandris/home-assistant-config>home-assistant-config</a><a class=skill-chip href=https://github.com/rozkalnsandris/balcony-irrigation-esp32>balcony-irrigation-esp32</a><a class=skill-chip href=https://github.com/rozkalnsandris/rozkalns-cv>rozkalns-cv</a><a class=skill-chip href=https://github.com/rozkalnsandris/ops-workflows>ops-workflows</a></div></details>
          <div class="skill-row"><a href=https://github.com/rozkalnsandris>github.com/rozkalnsandris ↗</a></div>
        </div>
      </section>'''
        text = text.replace(marker, block + "\n\n" + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_responsive() -> None:
    path = Path("frontend/styles/responsive.css")
    text = path.read_text(encoding="utf-8")
    old = 'grid-template-areas: "projects skills" "experience experience";'
    new = 'grid-template-areas: "projects skills" "projects github" "experience experience";'
    if old in text:
        text = text.replace(old, new, 1)
    if "#github-projects { grid-area: github; }" not in text:
        marker = "  #skills { grid-area: skills; }\n"
        if text.count(marker) != 1:
            raise SystemExit("skills grid marker mismatch")
        text = text.replace(marker, marker + "  #github-projects { grid-area: github; }\n", 1)
    path.write_text(text, encoding="utf-8")


def patch_python_test() -> None:
    Path("tests/test_github_project_links.py").write_text('''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nINDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")\n\n\nclass GitHubProjectLinksTest(unittest.TestCase):\n    def test_public_repo_proof_uses_sidebar_and_excludes_private_repos(self) -> None:\n        self.assertIn('<section id="github-projects">', INDEX)\n        self.assertIn('rel=me>GitHub</a>', INDEX)\n        selected = ("hermes-tech", "RPi5_main", "hermes-deals", "rozkalns-control-center", "dashboard_RPi5")\n        remaining = ("home-assistant-config", "balcony-irrigation-esp32", "rozkalns-cv", "ops-workflows")\n        for repo in (*selected, *remaining):\n            self.assertIn(f"https://github.com/rozkalnsandris/{repo}", INDEX)\n        self.assertIn('<details class="skill-row">', INDEX)\n        self.assertNotIn("YouTube_Marcim", INDEX)\n        self.assertNotIn("hermes-email-skill", INDEX)\n        self.assertNotIn("api.github.com", INDEX)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")


def patch_browser_test() -> None:
    path = Path("tests/browser-smoke.mjs")
    text = path.read_text(encoding="utf-8")
    old = '''        assert.equal(\n          await cdp.evaluate(`document.querySelector('a[rel="me"]')?.textContent`),\n          "GitHub · hermes-tech · RPi5_main · hermes-deals · control-center",\n          `responsive ${viewport.width}px ${locale.label} GitHub projects proof`\n        );'''
    new = '''        const githubProof = await cdp.evaluate(`(() => ({\n          profile: document.querySelector('a[rel="me"]')?.textContent.trim(),\n          selected: [...document.querySelectorAll('#github-projects > .skill-list > .skill-row:first-child a')].map((link) => link.textContent.trim()),\n          remaining: [...document.querySelectorAll('#github-projects details a')].map((link) => link.textContent.trim()),\n          collapsed: document.querySelector('#github-projects details')?.open === false\n        }))()`);\n        assert.equal(githubProof.profile, "GitHub", `responsive ${viewport.width}px ${locale.label} GitHub profile link`);\n        assert.deepEqual(githubProof.selected, ["hermes-tech", "RPi5_main", "hermes-deals", "rozkalns-control-center", "dashboard_RPi5"]);\n        assert.deepEqual(githubProof.remaining, ["home-assistant-config", "balcony-irrigation-esp32", "rozkalns-cv", "ops-workflows"]);\n        assert.equal(githubProof.collapsed, true);'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "const githubProof = await cdp.evaluate" not in text:
        raise SystemExit("browser GitHub assertion marker mismatch")
    path.write_text(text, encoding="utf-8")


patch_index()
patch_responsive()
patch_python_test()
patch_browser_test()
