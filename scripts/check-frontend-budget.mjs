import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const HTML_ROOT = join(ROOT, "html");
const manifest = JSON.parse(await readFile(join(ROOT, "frontend-dist-manifest.json"), "utf8"));
const LANGUAGES = ["en", "de", "lv"];
const LIMITS = {
  initialRawBytes: 128 * 1024,
  localizedHtmlBytes: 40 * 1024,
  localeJsonBytes: 16 * 1024,
  appScriptBytes: 24 * 1024,
  stylesheetBytes: 48 * 1024,
  photoBytes: 32 * 1024
};

async function size(relativePath) {
  return (await stat(join(HTML_ROOT, relativePath))).size;
}

function entry(key) {
  const value = manifest[key];
  assert.ok(value && typeof value === "object", `missing manifest entry: ${key}`);
  return value;
}

function collectStaticFiles(key, files = new Set()) {
  const value = entry(key);
  if (value.file) files.add(value.file);
  for (const file of value.css || []) files.add(file);
  for (const imported of value.imports || []) collectStaticFiles(imported, files);
  return files;
}

const initialFiles = collectStaticFiles("index.html");
for (const file of entry("index.html").assets || []) initialFiles.add(file);
const appFile = entry("index.html").file;
const photoFile = (entry("index.html").assets || []).find((file) => file.endsWith(".webp"));
const stylesheetFile = [...initialFiles].find((file) => file.endsWith(".css"));
assert.ok(photoFile, "missing initial photo asset");
assert.ok(stylesheetFile, "missing initial stylesheet asset");

assert.ok(await size(appFile) <= LIMITS.appScriptBytes, `app script budget exceeded: ${appFile}`);
assert.ok(await size(photoFile) <= LIMITS.photoBytes, `photo budget exceeded: ${photoFile}`);
assert.ok(await size(stylesheetFile) <= LIMITS.stylesheetBytes, `stylesheet budget exceeded: ${stylesheetFile}`);

for (const language of LANGUAGES) {
  const localizedPath = manifest._localized?.[language]?.path;
  assert.ok(localizedPath, `missing localized HTML path: ${language}`);
  const translationPath = entry(`../content/translations/${language}.json`).file;
  const htmlBytes = await size(localizedPath);
  const translationBytes = await size(translationPath);
  assert.ok(htmlBytes <= LIMITS.localizedHtmlBytes, `${language} localized HTML budget exceeded: ${htmlBytes}`);
  assert.ok(translationBytes <= LIMITS.localeJsonBytes, `${language} locale JSON budget exceeded: ${translationBytes}`);

  let initialRawBytes = htmlBytes + translationBytes;
  for (const file of initialFiles) initialRawBytes += await size(file);
  assert.ok(initialRawBytes <= LIMITS.initialRawBytes, `${language} initial raw payload budget exceeded: ${initialRawBytes}`);
  console.log(`FRONTEND_BUDGET=${language}:${initialRawBytes}/${LIMITS.initialRawBytes}`);
}

console.log("FRONTEND_BUDGET=PASS");
