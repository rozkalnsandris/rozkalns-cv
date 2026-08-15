from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tests/frontend.test.mjs"
text = path.read_text(encoding="utf-8")
old = '''test("chat and contact stay behind interaction-only dynamic imports", async () => {
  const source = await readFile(resolve(ROOT, "frontend/app.mjs"), "utf8");
  assert.doesNotMatch(source, /^import[\\s\\S]*?from "\\.\\/features\\/chat\\.mjs";/m);
  assert.doesNotMatch(source, /^import[\\s\\S]*?from "\\.\\/features\\/contact\\.mjs";/m);
  assert.match(source, /import\\("\\.\\/features\\/chat\\.mjs"\\)/);
  assert.match(source, /import\\("\\.\\/features\\/contact\\.mjs"\\)/);
  assert.match(source, /from "\\.\\/features\\/stats\\.mjs";/);
  assert.match(source, /bindStatsVisibility\\(stats\\)/);
  assert.match(source, /if \\(applied\\) stats\\.rerender\\(\\);/);
});

test("page entrypoints use contained language switching only", async () => {
  for (const sourcePath of ["frontend/app.mjs", "frontend/smarthome.mjs"]) {
    const source = await readFile(resolve(ROOT, sourcePath), "utf8");
    assert.match(source, /languageController\\.tryApply\\(button\\.dataset\\.lang\\)/, sourcePath);
    assert.doesNotMatch(source, /languageController\\.apply\\(/, sourcePath);
  }
});'''
new = '''test("chat and contact stay behind interaction-only dynamic imports", async () => {
  const source = await readFile(resolve(ROOT, "frontend/app.mjs"), "utf8");
  assert.doesNotMatch(source, /^import[\\s\\S]*?from "\\.\\/features\\/chat\\.mjs";/m);
  assert.doesNotMatch(source, /^import[\\s\\S]*?from "\\.\\/features\\/contact\\.mjs";/m);
  assert.match(source, /import\\("\\.\\/features\\/chat\\.mjs"\\)/);
  assert.match(source, /import\\("\\.\\/features\\/contact\\.mjs"\\)/);
  assert.match(source, /from "\\.\\/features\\/stats\\.mjs";/);
  assert.match(source, /bindStatsVisibility\\(stats\\)/);
});

test("page entrypoints keep language state inside their intended routing model", async () => {
  const mainSource = await readFile(resolve(ROOT, "frontend/app.mjs"), "utf8");
  assert.match(mainSource, /initialLanguage: document\\.documentElement\\.lang/);
  assert.match(mainSource, /languageController\\.tryApply\\(languageController\\.language\\)/);
  assert.doesNotMatch(mainSource, /querySelectorAll\\("\\[data-lang\\]"\\)/);
  assert.doesNotMatch(mainSource, /languageController\\.apply\\(/);

  const smartHomeSource = await readFile(resolve(ROOT, "frontend/smarthome.mjs"), "utf8");
  assert.match(smartHomeSource, /languageController\\.tryApply\\(button\\.dataset\\.lang\\)/);
  assert.doesNotMatch(smartHomeSource, /languageController\\.apply\\(/);
});'''
if text.count(old) != 1:
    raise SystemExit("tests/frontend.test.mjs: expected legacy language-switch contract block missing")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
