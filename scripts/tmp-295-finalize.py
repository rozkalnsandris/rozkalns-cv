from pathlib import Path


def replace_once(path, old, new):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement target, got {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


index = Path("frontend/index.html")
old_section = '<section id="github-projects"><div class=section-heading><h2>GitHub projects</h2></div><div class=skill-list><a href=//github.com/rozkalnsandris/hermes-tech>hermes-tech</a><a href=//github.com/rozkalnsandris/RPi5_main>RPi5_main</a><a href=//github.com/rozkalnsandris/hermes-deals>hermes-deals</a><a href=//github.com/rozkalnsandris/rozkalns-control-center>rozkalns-control-center</a><a href=//github.com/rozkalnsandris/dashboard_RPi5>dashboard_RPi5</a></div><details><summary class=org>+4</summary>home-assistant-config · balcony-irrigation-esp32 · rozkalns-cv · ops-workflows</details></section>'
new_section = '<section id="github-projects"><div class=section-heading><h2>GitHub projects</h2></div><div class=skill-list><a href=//github.com/rozkalnsandris/hermes-tech>hermes-tech</a><a href=//github.com/rozkalnsandris/RPi5_main>RPi5_main</a><a href=//github.com/rozkalnsandris/hermes-deals>hermes-deals</a><a href=//github.com/rozkalnsandris/rozkalns-control-center>rozkalns-control-center</a><a href=//github.com/rozkalnsandris/dashboard_RPi5>dashboard_RPi5</a></div><details><summary class=org>+4</summary><div class=skill-list><a href=//github.com/rozkalnsandris/home-assistant-config>home-assistant-config</a><a href=//github.com/rozkalnsandris/balcony-irrigation-esp32>balcony-irrigation-esp32</a><a href=//github.com/rozkalnsandris/rozkalns-cv>rozkalns-cv</a><a href=//github.com/rozkalnsandris/ops-workflows>ops-workflows</a></div></details></section>'
replace_once(index, old_section, new_section)

build = Path("scripts/build-frontend.mjs")
marker = "async function removeGeneratedFrontend() {"
helpers = '''const translationSources = Object.freeze(LOCALIZED_LANGUAGES.map((language) =>
  resolve(root, "content", "translations", `${language}.json`)
));

async function withMinifiedTranslationSources(buildFrontend) {
  const originals = await Promise.all(translationSources.map((path) => readFile(path, "utf8")));
  try {
    await Promise.all(translationSources.map((path, index) =>
      writeFile(path, JSON.stringify(JSON.parse(originals[index])))
    ));
    await buildFrontend();
  } finally {
    await Promise.all(translationSources.map((path, index) => writeFile(path, originals[index])));
  }
}

async function compactGeneratedHtml() {
  const paths = [
    resolve(html, "index.html"),
    resolve(html, "smarthome.html"),
    ...LOCALIZED_LANGUAGES.map((language) => resolve(html, language, "index.html"))
  ];
  await Promise.all(paths.map(async (path) => {
    const source = await readFile(path, "utf8");
    await writeFile(path, source.replace(/^[ \\t]+/gm, ""));
  }));
}

'''
text = build.read_text(encoding="utf-8")
if text.count(marker) != 1:
    raise SystemExit("build-frontend helper insertion marker mismatch")
text = text.replace(marker, helpers + marker)
old_tail = '''await removeGeneratedFrontend();
await build({ configFile: resolve(root, "vite.config.mjs") });
await verifyGeneratedShape();
await renderLocalizedPages({ root, htmlRoot: html });
await bindLocalizedIdentity();'''
new_tail = '''await removeGeneratedFrontend();
await withMinifiedTranslationSources(() => build({ configFile: resolve(root, "vite.config.mjs") }));
await verifyGeneratedShape();
await renderLocalizedPages({ root, htmlRoot: html });
await compactGeneratedHtml();
await bindLocalizedIdentity();'''
if text.count(old_tail) != 1:
    raise SystemExit("build-frontend tail mismatch")
build.write_text(text.replace(old_tail, new_tail), encoding="utf-8")

test_path = Path("tests/frontend.test.mjs")
test_text = test_path.read_text(encoding="utf-8")
old_contract = '''  assert.match(section, /class=skill-list/);
  assert.equal((section.match(/href=\\/\\/github\\.com\\/rozkalnsandris\\//g) || []).length, 5);
  assert.match(section, /<details><summary class=org>\\+4<\\/summary>/);'''
new_contract = '''  const featured = section.match(/<div class=skill-list>([\\s\\S]*?)<\\/div>/)?.[1] || "";
  assert.equal((featured.match(/href=\\/\\/github\\.com\\/rozkalnsandris\\//g) || []).length, 5);
  assert.equal((section.match(/href=\\/\\/github\\.com\\/rozkalnsandris\\//g) || []).length, 9);
  assert.match(section, /<details><summary class=org>\\+4<\\/summary><div class=skill-list>/);'''
if test_text.count(old_contract) != 1:
    raise SystemExit(f"frontend test contract target mismatch: {test_text.count(old_contract)}")
test_text = test_text.replace(old_contract, new_contract)
if "GitHub project overflow exposes direct repository links" in test_text:
    raise SystemExit("frontend #295 test already exists")
test_text += '''\n\ntest("GitHub project overflow exposes direct repository links", async () => {
  const source = await readFile(resolve(ROOT, "frontend/index.html"), "utf8");
  const section = source.match(/<section id="github-projects">([\\s\\S]*?)<\\/section>/)?.[1] || "";
  assert.match(section, /<details><summary class=org>\\+4<\\/summary><div class=skill-list>/);
  for (const repo of ["home-assistant-config", "balcony-irrigation-esp32", "rozkalns-cv", "ops-workflows"]) {
    assert.ok(section.includes(`href=//github.com/rozkalnsandris/${repo}>${repo}</a>`), repo);
  }
});
'''
test_path.write_text(test_text, encoding="utf-8")
