import { createHash } from "node:crypto";
import { cp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { build } from "vite";

const root = resolve(import.meta.dirname, "..");
const html = resolve(root, "html");
const viteManifest = resolve(html, ".vite", "manifest.json");
const committedManifest = resolve(root, "frontend-dist-manifest.json");
const nginxConfig = resolve(root, "nginx.conf");
const productionOrigin = "https://rozkalns.net";

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

async function bindIndexRepresentation(manifest) {
  const appFile = manifest["index.html"]?.file;
  if (!/^assets\/app\.[0-9a-f]{12}\.mjs$/.test(appFile || "")) {
    throw new Error(`unexpected app entry: ${String(appFile)}`);
  }
  const photoFile = manifest["photo.webp"]?.file;
  if (!/^assets\/photo\.[0-9a-f]{12}\.webp$/.test(photoFile || "")) {
    throw new Error(`unexpected profile image asset: ${String(photoFile)}`);
  }
  const nginxDigest = createHash("sha256")
    .update(await readFile(nginxConfig))
    .digest("hex")
    .slice(0, 12);
  const indexPath = resolve(html, "index.html");
  const source = await readFile(indexPath, "utf8");
  const appNeedle = `src="/${appFile}"`;
  if (source.split(appNeedle).length !== 2) {
    throw new Error(`generated index must reference app entry exactly once: ${appFile}`);
  }
  const previewNeedle = `<meta property="og:image" content="/${photoFile}">`;
  if (source.split(previewNeedle).length !== 2) {
    throw new Error(`generated index must reference profile image exactly once: ${photoFile}`);
  }
  const bound = source
    .replace(appNeedle, `src="/${appFile}?cfg=${nginxDigest}"`)
    .replace(
      previewNeedle,
      `<meta property="og:image" content="${productionOrigin}/${photoFile}">`
    );
  await writeFile(indexPath, bound);
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
  const representation = await bindIndexRepresentation(manifest);
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
