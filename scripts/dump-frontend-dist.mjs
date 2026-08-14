import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const tracked = [
  "frontend-dist-manifest.json",
  "html/index.html",
  "html/smarthome.html"
];
const untracked = execFileSync(
  "git",
  ["ls-files", "--others", "--exclude-standard", "-z", "html/assets", "html/i18n"],
  { encoding: "buffer" }
).toString("utf8").split("\0").filter(Boolean);

for (const path of [...new Set([...tracked, ...untracked])].sort()) {
  const base64 = readFileSync(path).toString("base64");
  console.log(`DIST_DUMP_BEGIN ${path}`);
  console.log(base64);
  console.log(`DIST_DUMP_END ${path}`);
}
