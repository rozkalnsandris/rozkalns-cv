import { cp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { build } from "vite";

const root = resolve(import.meta.dirname, "..");
const html = resolve(root, "html");
const viteManifest = resolve(html, ".vite", "manifest.json");
const committedManifest = resolve(root, "frontend-dist-manifest.json");

async function removeGeneratedFrontend() {
  await Promise.all([
    rm(resolve(html, "assets"), { recursive: true, force: true }),
    rm(resolve(html, "i18n"), { recursive: true, force: true }),
    rm(resolve(html, ".vite"), { recursive: true, force: true }),
    rm(resolve(html, "index.html"), { force: true }),
    rm(resolve(html, "smarthome.html"), { force: true }),
    rm(committedManifest, { force: true })
  ]);
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
  await cp(viteManifest, committedManifest);
  await rm(resolve(html, ".vite"), { recursive: true, force: true });
  await writeFile(committedManifest, `${JSON.stringify(JSON.parse(await readFile(committedManifest, "utf8")), null, 2)}\n`);
}

await removeGeneratedFrontend();
await build({ configFile: resolve(root, "vite.config.mjs") });
await verifyGeneratedShape();
console.log("FRONTEND_BUILD=PASS");
