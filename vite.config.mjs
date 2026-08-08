import { resolve } from "node:path";
import { defineConfig } from "vite";

const projectRoot = new URL(".", import.meta.url).pathname;
const frontendRoot = resolve(projectRoot, "frontend");
const outputRoot = resolve(projectRoot, "html");

export default defineConfig({
  root: frontendRoot,
  base: "/",
  publicDir: false,
  build: {
    outDir: outputRoot,
    emptyOutDir: false,
    manifest: true,
    assetsInlineLimit: 0,
    rolldownOptions: {
      input: {
        app: resolve(frontendRoot, "index.html"),
        smarthome: resolve(frontendRoot, "smarthome.html")
      },
      output: {
        hashCharacters: "hex",
        entryFileNames: "assets/[name].[hash:12].mjs",
        chunkFileNames: "assets/[name].[hash:12].mjs",
        assetFileNames(assetInfo) {
          const sources = assetInfo.originalFileNames || [];
          if (sources.some((name) => name.includes("content/translations/"))) {
            return "i18n/[name].[hash:12][extname]";
          }
          return "assets/[name].[hash:12][extname]";
        }
      }
    }
  }
});
