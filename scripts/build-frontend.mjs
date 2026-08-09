import { createHash } from "node:crypto";
import { cp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { build } from "vite";

const root = resolve(import.meta.dirname, "..");
const html = resolve(root, "html");
const viteManifest = resolve(html, ".vite", "manifest.json");
const committedManifest = resolve(root, "frontend-dist-manifest.json");
const nginxConfig = resolve(root, "nginx.conf");

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
  const chatFile = manifest["features/chat.mjs"].file;
  console.log("DEBUG_CHAT_RAW_BEGIN");
  console.log(await readFile(resolve(html, chatFile), "utf8"));
  console.log("DEBUG_CHAT_RAW_END");
  await cp(viteManifest, committedManifest);
  await rm(resolve(html, ".vite"), { recursive: true, force: true });
  await writeFile(
    committedManifest,
    `${JSON.stringify(JSON.parse(await readFile(committedManifest, "utf8")), null, 2)}\n`
  );
  console.log(`FRONTEND_NGINX_REPRESENTATION=${representation}`);
}

await removeGeneratedFrontend();
await build({ configFile: resolve(root, "vite.config.mjs") });
await verifyGeneratedShape();
console.log("FRONTEND_BUILD=PASS");
