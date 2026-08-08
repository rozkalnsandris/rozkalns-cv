import assert from "node:assert/strict";
import { readFile, readdir, stat } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const htmlRoot = resolve(root, "html");
const manifest = JSON.parse(await readFile(resolve(root, "frontend-dist-manifest.json"), "utf8"));
const HASHED = /\.[0-9a-f]{12}\.(?:mjs|js|css|json)$/;

const indexEntry = manifest["index.html"];
const smartEntry = manifest["smarthome.html"];
assert.equal(indexEntry?.isEntry, true, "manifest index.html entry is missing");
assert.equal(smartEntry?.isEntry, true, "manifest smarthome.html entry is missing");
assert.match(indexEntry.file, /^assets\/app\.[0-9a-f]{12}\.mjs$/);
assert.match(smartEntry.file, /^assets\/smarthome\.[0-9a-f]{12}\.mjs$/);

for (const language of ["en", "de", "lv"]) {
  const row = manifest[`../content/translations/${language}.json`];
  assert.ok(row, `manifest translation entry missing: ${language}`);
  assert.match(row.file, new RegExp(`^i18n/${language}\\.[0-9a-f]{12}\\.json$`));
}

const referenced = new Set();
for (const row of Object.values(manifest)) {
  if (typeof row?.file === "string") referenced.add(row.file);
  for (const key of ["css", "assets"]) {
    for (const file of row?.[key] || []) referenced.add(file);
  }
}

async function filesUnder(directory, prefix) {
  return (await readdir(resolve(htmlRoot, directory), { withFileTypes: true }))
    .filter((entry) => entry.isFile())
    .map((entry) => `${prefix}/${entry.name}`)
    .sort();
}

const actualAssets = await filesUnder("assets", "assets");
const actualI18n = await filesUnder("i18n", "i18n");
for (const file of [...actualAssets, ...actualI18n]) {
  assert.match(file, HASHED, `generated asset is not content-hashed: ${file}`);
  assert.ok(referenced.has(file), `generated asset is not referenced by manifest: ${file}`);
}
for (const file of referenced) {
  await stat(resolve(htmlRoot, file));
}
assert.deepEqual(
  [...new Set([...actualAssets, ...actualI18n])].sort(),
  [...referenced].sort(),
  "generated asset directories contain stale or missing files"
);

const indexHtml = await readFile(resolve(htmlRoot, "index.html"), "utf8");
const smartHtml = await readFile(resolve(htmlRoot, "smarthome.html"), "utf8");
for (const [name, text] of [["index", indexHtml], ["smarthome", smartHtml]]) {
  assert.doesNotMatch(text, /(?:src|href)="\.\//, `${name} HTML still contains source-relative frontend references`);
  assert.doesNotMatch(text, /\?cfg=[0-9a-f]{12}/, `${name} HTML still contains manual cache-bust query`);
  for (const path of text.matchAll(/(?:src|href)="\/(assets\/[^"?#]+)/g)) {
    assert.ok(referenced.has(path[1]), `${name} HTML references an asset outside the manifest: ${path[1]}`);
  }
}
assert.ok(indexHtml.includes(`/${indexEntry.file}`), "index HTML does not reference manifest entry");
assert.ok(smartHtml.includes(`/${smartEntry.file}`), "Smart Home HTML does not reference manifest entry");

for (const source of [
  "frontend/index.html",
  "frontend/smarthome.html",
  "frontend/app.mjs",
  "frontend/smarthome.mjs"
]) {
  const text = await readFile(resolve(root, source), "utf8");
  assert.doesNotMatch(text, /\/(?:assets|i18n)\/[^"'`\s]+\.[0-9a-f]{12}\./, `${source} contains a generated fingerprint`);
}

async function totalBytes(paths) {
  let total = 0;
  for (const file of paths) total += (await stat(resolve(htmlRoot, file))).size;
  return total;
}
const js = actualAssets.filter((file) => /\.m?js$/.test(file));
const css = actualAssets.filter((file) => file.endsWith(".css"));
const budgets = {
  javascript: [await totalBytes(js), 25_000],
  css: [await totalBytes(css), 22_000],
  translations: [await totalBytes(actualI18n), 22_000],
  indexHtml: [(await stat(resolve(htmlRoot, "index.html"))).size, 21_000],
  smartHomeHtml: [(await stat(resolve(htmlRoot, "smarthome.html"))).size, 5_000]
};
for (const [name, [bytes, limit]] of Object.entries(budgets)) {
  assert.ok(bytes <= limit, `${name} exceeds budget: ${bytes} > ${limit}`);
  console.log(`FRONTEND_BUDGET_${name.toUpperCase()}=${bytes}/${limit}`);
}

console.log(`FRONTEND_MANIFEST_ASSETS=${referenced.size}`);
console.log("FRONTEND_DIST_CONTRACT=PASS");
