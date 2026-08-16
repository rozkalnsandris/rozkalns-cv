from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

index_path = ROOT / "frontend" / "index.html"
index = index_path.read_text(encoding="utf-8")
old = '<a href="https://github.com/rozkalnsandris" rel="me">github.com/rozkalnsandris</a>'
new = '<a href=https://github.com/rozkalnsandris rel=me>GitHub · hermes-tech · RPi5_main · hermes-deals · control-center</a>'
assert index.count(old) == 1, "GitHub profile link marker changed"
index = index.replace(old, new)
index_path.write_text(index, encoding="utf-8")

browser_path = ROOT / "tests" / "browser-smoke.mjs"
browser = browser_path.read_text(encoding="utf-8")
browser_marker = '''        await cdp.waitFor(\n          `["rail", "inline"].includes(document.querySelector('#chatLauncher')?.dataset.placement)`,\n          10_000,\n          `responsive ${viewport.width}px ${locale.label} launcher placement`\n        );\n        const layout = await cdp.evaluate(`(() => {\n'''
assert browser.count(browser_marker) == 1, "responsive launcher marker changed"
browser = browser.replace(
    browser_marker,
    '''        await cdp.waitFor(\n          `["rail", "inline"].includes(document.querySelector('#chatLauncher')?.dataset.placement)`,\n          10_000,\n          `responsive ${viewport.width}px ${locale.label} launcher placement`\n        );\n        assert.equal(\n          await cdp.evaluate(`document.querySelector('a[rel="me"]')?.textContent`),\n          "GitHub · hermes-tech · RPi5_main · hermes-deals · control-center",\n          `responsive ${viewport.width}px ${locale.label} GitHub projects proof`\n        );\n        const layout = await cdp.evaluate(`(() => {\n''',
)
browser_path.write_text(browser, encoding="utf-8")

test_path = ROOT / "tests" / "test_github_project_links.py"
test_path.write_text('''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nINDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")\n\n\nclass GitHubProjectLinksTest(unittest.TestCase):\n    def test_compact_public_repo_proof_uses_existing_profile_link(self) -> None:\n        self.assertIn("https://github.com/rozkalnsandris", INDEX)\n        for repo in ("hermes-tech", "RPi5_main", "hermes-deals", "control-center"):\n            self.assertIn(repo, INDEX)\n        self.assertNotIn("YouTube_Marcim", INDEX)\n        self.assertNotIn("hermes-email-skill", INDEX)\n        self.assertNotIn("api.github.com", INDEX)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")
