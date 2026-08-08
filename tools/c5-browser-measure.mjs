import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { extname, join, normalize, resolve, sep } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const HTML_ROOT = join(ROOT, "html");
const CHROME_BIN = process.env.CHROME_BIN;
const OUTPUT = process.env.C5_OUTPUT || join(ROOT, "c5-post-c4-baseline.json");
if (!CHROME_BIN) throw new Error("CHROME_BIN is required");
if (typeof WebSocket !== "function") throw new Error("Node WebSocket is required");

const MIME = new Map([
  [".html", "text/html; charset=utf-8"], [".css", "text/css; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"], [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"], [".svg", "image/svg+xml"],
  [".jpg", "image/jpeg"], [".jpeg", "image/jpeg"], [".png", "image/png"],
  [".pdf", "application/pdf"]
]);

function safePath(pathname) {
  const decoded = decodeURIComponent(pathname === "/" ? "/index.html" : pathname);
  const relative = normalize(decoded).replace(/^([/\\])+/, "");
  const target = resolve(HTML_ROOT, relative);
  if (target !== HTML_ROOT && !target.startsWith(`${HTML_ROOT}${sep}`)) throw new Error("unsafe path");
  return target;
}

function statsPayload() {
  return {
    updated: new Date().toISOString(), uptime_30d: 99.95, docker_containers: 16,
    load1: 0.42, days_online: 37, cpu_usage: 8.5, ram_usage: 41.2,
    disk_usage: 32.1, cpu_temp: 49.6
  };
}

function listen(server) {
  return new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolveListen(server.address());
    });
  });
}
function closeServer(server) { return new Promise((resolveClose) => server.close(resolveClose)); }

function createFixtureServer() {
  return createServer(async (request, response) => {
    try {
      const url = new URL(request.url || "/", "http://127.0.0.1");
      if (url.pathname === "/stats.json") {
        const body = Buffer.from(JSON.stringify(statsPayload()));
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store",
          "Content-Length": String(body.length)
        });
        response.end(body);
        return;
      }
      if (url.pathname.startsWith("/api/")) {
        response.writeHead(404, { "Cache-Control": "no-store" });
        response.end();
        return;
      }
      if (request.method !== "GET" && request.method !== "HEAD") {
        response.writeHead(405); response.end(); return;
      }
      const target = safePath(url.pathname);
      const metadata = await stat(target);
      if (!metadata.isFile()) throw new Error("not file");
      const body = await readFile(target);
      response.writeHead(200, {
        "Content-Type": MIME.get(extname(target)) || "application/octet-stream",
        "Cache-Control": "public, max-age=3600",
        "Content-Length": String(body.length)
      });
      response.end(request.method === "HEAD" ? undefined : body);
    } catch {
      response.writeHead(404, { "Content-Type": "text/plain" }); response.end("not found");
    }
  });
}

async function readDebugPort(profile, timeoutMs = 15000) {
  const path = join(profile, "DevToolsActivePort");
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const [line] = (await readFile(path, "utf8")).trim().split(/\r?\n/);
      if (/^[0-9]+$/.test(line)) return Number(line);
    } catch {}
    await delay(50);
  }
  throw new Error("Chrome debug port timeout");
}
async function jsonRetry(url, options = {}) {
  let error;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return await response.json();
      error = new Error(`${response.status} ${response.statusText}`);
    } catch (caught) { error = caught; }
    await delay(50);
  }
  throw error || new Error(`failed ${url}`);
}
async function stop(child) {
  if (child.exitCode !== null) return;
  child.kill("SIGTERM");
  await Promise.race([new Promise((resolveExit) => child.once("exit", resolveExit)), delay(2000)]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

class Cdp {
  constructor(url) { this.ws = new WebSocket(url); this.id = 1; this.pending = new Map(); this.events = new Map(); }
  async open() {
    await new Promise((resolveOpen, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP open timeout")), 10000);
      this.ws.addEventListener("open", () => { clearTimeout(timer); resolveOpen(); }, { once: true });
      this.ws.addEventListener("error", () => { clearTimeout(timer); reject(new Error("CDP websocket error")); }, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const pending = this.pending.get(message.id); if (!pending) return;
        this.pending.delete(message.id);
        message.error ? pending.reject(new Error(message.error.message)) : pending.resolve(message.result || {});
        return;
      }
      for (const callback of this.events.get(message.method) || []) callback(message.params || {});
    });
  }
  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolveSend, reject) => {
      this.pending.set(id, { resolve: resolveSend, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  wait(method, timeoutMs = 15000) {
    return new Promise((resolveEvent, reject) => {
      const set = this.events.get(method) || new Set();
      const callback = (params) => { clearTimeout(timer); set.delete(callback); resolveEvent(params); };
      const timer = setTimeout(() => { set.delete(callback); reject(new Error(`timeout ${method}`)); }, timeoutMs);
      set.add(callback); this.events.set(method, set);
    });
  }
  async eval(expression) {
    const result = await this.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "browser eval failed");
    return result.result?.value;
  }
  async navigate(url) { const loaded = this.wait("Page.loadEventFired"); await this.send("Page.navigate", { url }); await loaded; }
  close() { this.ws.close(); }
}

function mergeRanges(ranges) {
  const sorted = ranges.filter((row) => row.count > 0).map((row) => [row.startOffset, row.endOffset]).sort((a,b) => a[0]-b[0]);
  const merged = [];
  for (const [start, end] of sorted) {
    const last = merged.at(-1);
    if (!last || start > last[1]) merged.push([start, end]);
    else last[1] = Math.max(last[1], end);
  }
  return merged.reduce((total, [start,end]) => total + end - start, 0);
}

async function runOnce(baseUrl, viewport, mode) {
  const profile = await mkdtemp(join(tmpdir(), "c5-chrome-"));
  const chrome = spawn(CHROME_BIN, [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
    "--disable-background-networking", "--disable-component-update", "--disable-default-apps",
    "--disable-sync", "--no-first-run", "--lang=en-US", "--remote-debugging-port=0",
    `--user-data-dir=${profile}`, "about:blank"
  ], { stdio: ["ignore", "ignore", "pipe"] });
  let cdp;
  try {
    const port = await readDebugPort(profile);
    const target = await jsonRetry(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
    cdp = new Cdp(target.webSocketDebuggerUrl); await cdp.open();
    await Promise.all([
      cdp.send("Page.enable"), cdp.send("Runtime.enable"), cdp.send("Network.enable"),
      cdp.send("Debugger.enable"), cdp.send("Profiler.enable")
    ]);
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: viewport.mobile
    });
    await cdp.send("Network.setBlockedURLs", { urls: ["*://static.cloudflareinsights.com/*", "*://cloudflareinsights.com/*"] });

    if (mode === "warm") {
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: false });
      await cdp.navigate(`${baseUrl}/`);
      await delay(1000);
    } else {
      await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
    }

    await cdp.send("Profiler.startPreciseCoverage", { callCount: true, detailed: true });
    await cdp.navigate(`${baseUrl}/`);
    await delay(1300);
    const ready = await cdp.eval(`({lang:document.documentElement.lang,live:document.querySelector('#liveDot')?.dataset.state})`);
    if (ready.lang !== "en" || ready.live !== "live") throw new Error(`page not ready ${JSON.stringify(ready)}`);

    const timing = await cdp.eval(`(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      const rows = [nav, ...performance.getEntriesByType('resource')].filter(Boolean);
      return {
        requests: rows.length,
        transferBytes: rows.reduce((sum,row) => sum + (row.transferSize || 0), 0),
        encodedBytes: rows.reduce((sum,row) => sum + (row.encodedBodySize || 0), 0),
        resources: rows.map(row => ({name:row.name, initiatorType:row.initiatorType, transferSize:row.transferSize||0, encodedBodySize:row.encodedBodySize||0}))
      };
    })()`);

    const coverage = await cdp.send("Profiler.takePreciseCoverage");
    await cdp.send("Profiler.stopPreciseCoverage");
    const scripts = [];
    for (const script of coverage.result || []) {
      if (!script.url.startsWith(baseUrl)) continue;
      const source = await cdp.send("Debugger.getScriptSource", { scriptId: script.scriptId });
      const total = source.scriptSource?.length || 0;
      const used = mergeRanges(script.functions.flatMap((fn) => fn.ranges || []));
      scripts.push({ url: script.url, totalBytes: total, usedBytes: used, usedPct: total ? used / total * 100 : 0 });
    }
    scripts.sort((a,b) => a.url.localeCompare(b.url));
    return { mode, viewport, ...timing, scripts };
  } finally {
    try { cdp?.close(); } catch {}
    await stop(chrome);
    await rm(profile, { recursive: true, force: true });
  }
}

function median(values) {
  const sorted = [...values].sort((a,b) => a-b);
  return sorted[Math.floor(sorted.length / 2)];
}
function summarize(samples) {
  const selected = samples.find((sample) => sample.transferBytes === median(samples.map((row) => row.transferBytes))) || samples[1];
  return {
    sampleCount: samples.length,
    medianRequests: median(samples.map((row) => row.requests)),
    medianTransferBytes: median(samples.map((row) => row.transferBytes)),
    medianEncodedBytes: median(samples.map((row) => row.encodedBytes)),
    representativeScripts: selected.scripts,
    representativeResources: selected.resources
  };
}

const server = createFixtureServer();
const address = await listen(server);
const baseUrl = `http://127.0.0.1:${address.port}`;
const viewports = {
  desktop: { width: 1440, height: 1000, mobile: false },
  phone: { width: 390, height: 844, mobile: true }
};
const output = { generatedAt: new Date().toISOString(), baseUrl: "local-fixture", runs: {} };
try {
  for (const [name, viewport] of Object.entries(viewports)) {
    output.runs[name] = {};
    for (const mode of ["cold", "warm"]) {
      const samples = [];
      for (let attempt = 0; attempt < 3; attempt++) samples.push(await runOnce(baseUrl, viewport, mode));
      output.runs[name][mode] = summarize(samples);
      console.log(`C5_${name.toUpperCase()}_${mode.toUpperCase()} requests=${output.runs[name][mode].medianRequests} transfer=${output.runs[name][mode].medianTransferBytes} encoded=${output.runs[name][mode].medianEncodedBytes}`);
    }
  }
  await import("node:fs/promises").then(({ writeFile }) => writeFile(OUTPUT, `${JSON.stringify(output, null, 2)}\n`));
  console.log(`C5_BASELINE_OUTPUT=${OUTPUT}`);
} finally {
  await closeServer(server);
}
