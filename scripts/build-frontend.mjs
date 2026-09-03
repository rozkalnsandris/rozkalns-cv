import { createHash } from "node:crypto";
import { cp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { build } from "vite";
import { LOCALIZED_LANGUAGES, renderLocalizedPages } from "./localize-frontend.mjs";

const root = resolve(import.meta.dirname, "..");
const html = resolve(root, "html");
const viteManifest = resolve(html, ".vite", "manifest.json");
const committedManifest = resolve(root, "frontend-dist-manifest.json");
const nginxConfig = resolve(root, "nginx.conf");
const localizedIdentityFiles = Object.freeze({
  en: "en/index.html",
  de: "de/index.html",
  lv: "lv/index.html",
  sitemap: "sitemap.xml"
});

const translationSources = Object.freeze(LOCALIZED_LANGUAGES.map((language) =>
  resolve(root, "content", "translations", `${language}.json`)
));

async function withMinifiedTranslationSources(buildFrontend) {
  const originals = await Promise.all(translationSources.map((path) => readFile(path, "utf8")));
  try {
    await Promise.all(translationSources.map((path, index) =>
      writeFile(path, JSON.stringify(Object.fromEntries(Object.entries(JSON.parse(originals[index])).filter(([key]) => !key.startsWith("pdf_")))))
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
    await writeFile(path, source.replace(/^[ \t]+/gm, ""));
  }));
}

async function removeGeneratedFrontend() {
  await Promise.all([
    rm(resolve(html, "assets"), { recursive: true, force: true }),
    rm(resolve(html, "i18n"), { recursive: true, force: true }),
    rm(resolve(html, ".vite"), { recursive: true, force: true }),
    rm(resolve(html, "index.html"), { force: true }),
    rm(resolve(html, "smarthome.html"), { force: true }),
    ...LOCALIZED_LANGUAGES.map((language) => rm(resolve(html, language), { recursive: true, force: true })),
    rm(committedManifest, { force: true })
  ]);
}

async function bindAppRepresentation(manifest) {
  const appFile = manifest["index.html"]?.file;
  if (!/^assets\/app\.[0-9a-f]{12}\.mjs$/.test(appFile || "")) {
    throw new Error(`unexpected app entry: ${String(appFile)}`);
  }
  const nginxDigest = createHash("sha256")
    .update(await readFile(nginxConfig))
    .digest("hex")
    .slice(0, 12);
  const indexPath = resolve(html, "index.html");
  const source = await readFile(indexPath, "utf8");
  const needle = `src="/${appFile}"`;
  if (source.split(needle).length !== 2) {
    throw new Error(`generated index must reference app entry exactly once: ${appFile}`);
  }
  await writeFile(indexPath, source.replace(needle, `src="/${appFile}?cfg=${nginxDigest}"`));
  return nginxDigest;
}

async function verifyGeneratedShape() {
  const manifest = JSON.parse(await readFile(viteManifest, "utf8"));
  const htmlEntries = await readdir(html);
  if (!htmlEntries.includes("index.html") || !htmlEntries.includes("smarthome.html")) {
    throw new Error("Vite did not emit both HTML entry points");
  }
  const manifestRows = Object.values(manifest);
  if (!manifestRows.some((row) => row?.isEntry && row?.file?.startsWith("assets/"))) {
    throw new Error("Vite manifest contains no frontend entry asset");
  }
  const representation = await bindAppRepresentation(manifest);
  await cp(viteManifest, committedManifest);
  await rm(resolve(html, ".vite"), { recursive: true, force: true });
  await writeFile(
    committedManifest,
    `${JSON.stringify(JSON.parse(await readFile(committedManifest, "utf8")), null, 2)}\n`
  );
  console.log(`FRONTEND_NGINX_REPRESENTATION=${representation}`);
}

async function bindLocalizedIdentity() {
  const manifest = JSON.parse(await readFile(committedManifest, "utf8"));
  manifest._localized = Object.fromEntries(await Promise.all(
    Object.entries(localizedIdentityFiles).map(async ([name, relative]) => [
      name,
      {
        path: relative,
        sha256: createHash("sha256").update(await readFile(resolve(html, relative))).digest("hex")
      }
    ])
  ));
  await writeFile(committedManifest, `${JSON.stringify(manifest, null, 2)}\n`);
}

await removeGeneratedFrontend();
await withMinifiedTranslationSources(() => build({ configFile: resolve(root, "vite.config.mjs") }));
await verifyGeneratedShape();
await renderLocalizedPages({ root, htmlRoot: html });
await compactGeneratedHtml();
await bindLocalizedIdentity();
console.log("FRONTEND_BUILD=PASS");
