import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((rows, value, index, source) => {
    if (index % 2 === 0) rows.push([value.replace(/^--/, ""), source[index + 1]]);
    return rows;
  }, [])
);
for (const key of ["output", "url", "chrome", "sha"]) {
  if (!args[key]) throw new Error(`--${key} required`);
}
const OUT = resolve(args.output);
const ORIGIN = new URL(args.url).origin;
const CHROME = resolve(args.chrome);
const SHA = args.sha;
if (!/^[0-9a-f]{40}$/.test(SHA) || typeof WebSocket !== "function") {
  throw new Error("invalid runtime");
}
await mkdir(OUT, { recursive: true });

class CDP {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.id = 1;
    this.pending = new Map();
    this.listeners = new Map();
  }
  async open() {
    await new Promise((resolveOpen, rejectOpen) => {
      this.ws.addEventListener("open", resolveOpen, { once: true });
      this.ws.addEventListener("error", () => rejectOpen(new Error("ws open failed")), { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        message.error ? pending.reject(new Error(message.error.message)) : pending.resolve(message.result || {});
        return;
      }
      for (const listener of this.listeners.get(message.method) || []) listener(message.params || {});
    });
  }
  on(method, listener) {
    const set = this.listeners.get(method) || new Set();
    set.add(listener);
    this.listeners.set(method, set);
    return () => set.delete(listener);
  }
  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolveSend, rejectSend) => {
      this.pending.set(id, { resolve: resolveSend, reject: rejectSend });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  waitEvent(method, timeoutMs = 15000) {
    return new Promise((resolveEvent, rejectEvent) => {
      let off;
      const timer = setTimeout(() => {
        off?.();
        rejectEvent(new Error(`timeout ${method}`));
      }, timeoutMs);
      off = this.on(method, (params) => {
        clearTimeout(timer);
        off();
        resolveEvent(params);
      });
    });
  }
  async eval(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true
    });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "eval failed");
    return result.result?.value;
  }
  async wait(expression, timeoutMs = 15000) {
    const end = Date.now() + timeoutMs;
    while (Date.now() < end) {
      if (await this.eval(expression)) return;
      await sleep(100);
    }
    throw new Error(`timeout: ${expression}`);
  }
  async navigate(url) {
    const loaded = this.waitEvent("Page.loadEventFired");
    await this.send("Page.navigate", { url });
    await loaded;
  }
  close() { this.ws.close(); }
}

async function debugPort(profile) {
  const file = join(profile, "DevToolsActivePort");
  const end = Date.now() + 20000;
  while (Date.now() < end) {
    try {
      const port = Number((await readFile(file, "utf8")).split(/\r?\n/)[0]);
      if (Number.isInteger(port) && port > 0) return port;
    } catch {}
    await sleep(100);
  }
  throw new Error("DevToolsActivePort timeout");
}

async function getJson(url, options = {}) {
  const end = Date.now() + 20000;
  while (Date.now() < end) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return await response.json();
    } catch {}
    await sleep(100);
  }
  throw new Error(`fetch timeout ${url}`);
}

async function stop(process) {
  if (process.exitCode !== null) return;
  const exited = new Promise((resolveExit) => process.once("exit", resolveExit));
  process.kill("SIGTERM");
  if (!await Promise.race([exited.then(() => true), sleep(3000).then(() => false)])) {
    process.kill("SIGKILL");
    await exited;
  }
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return url.origin === ORIGIN ? url.pathname + url.search : url.origin + url.pathname;
  } catch {
    return "<invalid>";
  }
}

function summarizeNetwork(map, phase) {
  const rows = [...map.values()]
    .filter((row) => row.phase === phase)
    .map((row) => ({
      url: safeUrl(row.url),
      method: row.method,
      type: row.type,
      status: row.status ?? null,
      mimeType: row.mime ?? null,
      bytes: Math.round(row.bytes || 0),
      cache: Boolean(row.disk || row.serviceWorker),
      failed: Boolean(row.failed)
    }))
    .sort((a, b) => a.url.localeCompare(b.url));
  return {
    requests: rows.length,
    transferredBytes: rows.reduce((sum, row) => sum + row.bytes, 0),
    cacheHits: rows.filter((row) => row.cache).length,
    rows
  };
}

function v8Used(functions, length) {
  const ranges = functions.flatMap((fn) => fn.ranges || []);
  const boundaries = [...new Set(ranges.flatMap((range) => [range.startOffset, range.endOffset]))]
    .filter((value) => value >= 0 && value <= length)
    .sort((a, b) => a - b);
  let used = 0;
  for (let index = 0; index < boundaries.length - 1; index++) {
    const start = boundaries[index];
    const end = boundaries[index + 1];
    const middle = (start + end) / 2;
    const covering = ranges
      .filter((range) => range.startOffset <= middle && range.endOffset >= middle)
      .sort((a, b) => (a.endOffset - a.startOffset) - (b.endOffset - b.startOffset))[0];
    if (covering?.count > 0) used += end - start;
  }
  return used;
}

async function performanceMetrics(client) {
  return await client.eval(`(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const paints = Object.fromEntries(performance.getEntriesByType('paint').map(e => [e.name, e.startTime]));
    const lcp = performance.getEntriesByType('largest-contentful-paint');
    const shifts = performance.getEntriesByType('layout-shift').filter(e => !e.hadRecentInput);
    return {
      ttfbMs: nav?.responseStart ?? null,
      dclMs: nav?.domContentLoadedEventEnd ?? null,
      loadMs: nav?.loadEventEnd ?? null,
      fcpMs: paints['first-contentful-paint'] ?? null,
      lcpMs: lcp.length ? lcp.at(-1).startTime : null,
      cls: shifts.reduce((sum, e) => sum + e.value, 0)
    };
  })()`);
}

async function run(name, viewport) {
  const profile = await mkdtemp(join(tmpdir(), `cv-c5-${name}-`));
  const process = spawn(CHROME, [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
    "--disable-background-networking", "--disable-component-update", "--disable-default-apps",
    "--disable-sync", "--no-first-run", "--lang=en-US", "--remote-debugging-port=0",
    `--user-data-dir=${profile}`, "about:blank"
  ], { stdio: ["ignore", "pipe", "pipe"] });
  let stderr = "";
  process.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
  let client;
  try {
    const port = await debugPort(profile);
    const version = await getJson(`http://127.0.0.1:${port}/json/version`);
    const target = await getJson(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
    client = new CDP(target.webSocketDebuggerUrl);
    await client.open();
    for (const domain of ["Page", "Runtime", "Network", "Profiler", "Debugger"]) {
      await client.send(`${domain}.enable`);
    }
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width, height: viewport.height, deviceScaleFactor: viewport.dpr,
      mobile: viewport.mobile, screenWidth: viewport.width, screenHeight: viewport.height
    });
    await client.send("Network.setCacheDisabled", { cacheDisabled: false });
    await client.send("Profiler.startPreciseCoverage", { callCount: true, detailed: true });

    const network = new Map();
    let phase = "cold";
    client.on("Network.requestWillBeSent", (event) => {
      network.set(event.requestId, {
        phase, url: event.request.url, method: event.request.method, type: event.type, bytes: 0
      });
    });
    client.on("Network.responseReceived", (event) => {
      const row = network.get(event.requestId);
      if (!row) return;
      row.status = event.response.status;
      row.mime = event.response.mimeType;
      row.disk = event.response.fromDiskCache;
      row.serviceWorker = event.response.fromServiceWorker;
    });
    client.on("Network.requestServedFromCache", (event) => {
      const row = network.get(event.requestId);
      if (row) row.disk = true;
    });
    client.on("Network.loadingFinished", (event) => {
      const row = network.get(event.requestId);
      if (row) row.bytes = event.encodedDataLength || 0;
    });
    client.on("Network.loadingFailed", (event) => {
      const row = network.get(event.requestId);
      if (row) row.failed = true;
    });

    await client.navigate(`${ORIGIN}/`);
    await client.wait("document.readyState === 'complete'", 15000);
    await sleep(1200);
    const cold = {
      metrics: await performanceMetrics(client),
      network: summarizeNetwork(network, "cold"),
      state: await client.eval(`(() => ({
        lang: document.documentElement.lang,
        hidden: document.hidden,
        statsState: document.querySelector('#liveDot')?.dataset.state ?? null,
        statsRendered: [...document.querySelectorAll('[data-stat]')].some(e => e.textContent.trim() !== '—')
      }))()`)
    };

    const precise = await client.send("Profiler.takePreciseCoverage");
    await client.send("Profiler.stopPreciseCoverage");
    const javascript = [];
    for (const script of precise.result || []) {
      if (!script.url) continue;
      let url;
      try { url = new URL(script.url); } catch { continue; }
      if (url.origin !== ORIGIN) continue;
      let source = "";
      try {
        source = (await client.send("Debugger.getScriptSource", { scriptId: script.scriptId })).scriptSource || "";
      } catch { continue; }
      const usedBytes = v8Used(script.functions || [], source.length);
      javascript.push({
        url: url.pathname + url.search,
        bytes: source.length,
        usedBytes,
        percent: source.length ? Number((100 * usedBytes / source.length).toFixed(2)) : null
      });
    }
    javascript.sort((a, b) => a.url.localeCompare(b.url));

    phase = "warm";
    await client.navigate(`${ORIGIN}/`);
    await client.wait("document.readyState === 'complete'", 15000);
    await sleep(1200);
    const warm = {
      metrics: await performanceMetrics(client),
      network: summarizeNetwork(network, "warm")
    };

    return {
      browser: version.Browser || null,
      viewport,
      cold,
      warm,
      coverage: { javascript }
    };
  } catch (error) {
    error.message += `\nChrome stderr tail:\n${stderr.slice(-3000)}`;
    throw error;
  } finally {
    client?.close();
    await stop(process);
    for (let attempt = 0; attempt < 3; attempt++) {
      try { await rm(profile, { recursive: true, force: true }); break; }
      catch { await sleep(300); }
    }
  }
}

const result = {
  schema: 1,
  baselineSha: SHA,
  capturedAt: new Date().toISOString(),
  origin: ORIGIN,
  desktop: await run("desktop", { width: 1440, height: 1000, dpr: 1, mobile: false }),
  phone: await run("phone", { width: 390, height: 844, dpr: 3, mobile: true }),
  privacy: { productionWrites: false, contactPosts: false, chatPosts: false }
};
await writeFile(join(OUT, "startup-baseline.json"), JSON.stringify(result, null, 2) + "\n");
console.log(`C5_BROWSER_SHA=${SHA}`);
console.log(`C5_DESKTOP_COLD_BYTES=${result.desktop.cold.network.transferredBytes}`);
console.log(`C5_DESKTOP_WARM_BYTES=${result.desktop.warm.network.transferredBytes}`);
console.log(`C5_PHONE_COLD_BYTES=${result.phone.cold.network.transferredBytes}`);
console.log(`C5_PHONE_WARM_BYTES=${result.phone.warm.network.transferredBytes}`);
