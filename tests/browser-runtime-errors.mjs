import assert from "node:assert/strict";
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
const HIGH_SEVERITY_CONSOLE_TYPES = new Set(["error", "assert"]);
const RUNTIME_SETTLE_MS = 200;

if (!CHROME_BIN) throw new Error("CHROME_BIN is required");
if (typeof WebSocket !== "function") {
  throw new Error("This test requires the Node.js WebSocket implementation");
}

const MIME_TYPES = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".webp", "image/webp"]
]);

const CLEAN_MATRIX = [
  { kind: "main", path: "/en/", language: "en", width: 1280, height: 900 },
  { kind: "main", path: "/en/", language: "en", width: 390, height: 844 },
  { kind: "main", path: "/de/", language: "de", width: 1280, height: 900 },
  { kind: "main", path: "/de/", language: "de", width: 390, height: 844 },
  { kind: "main", path: "/lv/", language: "lv", width: 1280, height: 900 },
  { kind: "main", path: "/lv/", language: "lv", width: 390, height: 844 },
  { kind: "proof", path: "/en/proof/", language: "en", width: 1280, height: 900 },
  { kind: "proof", path: "/en/proof/", language: "en", width: 390, height: 844 },
  { kind: "proof", path: "/de/proof/", language: "de", width: 1280, height: 900 },
  { kind: "proof", path: "/de/proof/", language: "de", width: 390, height: 844 },
  { kind: "proof", path: "/lv/proof/", language: "lv", width: 1280, height: 900 },
  { kind: "proof", path: "/lv/proof/", language: "lv", width: 390, height: 844 },
  { kind: "smarthome", path: "/smarthome.html", language: "en", width: 1280, height: 900 },
  { kind: "smarthome", path: "/smarthome.html", language: "en", width: 390, height: 844 }
];

function listen(server) {
  return new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolveListen(server.address());
    });
  });
}

function closeServer(server) {
  return new Promise((resolveClose, reject) => {
    server.close((error) => error ? reject(error) : resolveClose());
  });
}

function safeStaticPath(pathname) {
  const routed = pathname.endsWith("/") ? `${pathname}index.html` : pathname;
  const decoded = decodeURIComponent(routed);
  const relative = normalize(decoded).replace(/^([/\\])+/, "");
  const target = resolve(HTML_ROOT, relative);
  if (target !== HTML_ROOT && !target.startsWith(`${HTML_ROOT}${sep}`)) {
    throw new Error("unsafe fixture path");
  }
  return target;
}

function statsPayload() {
  return {
    updated: new Date().toISOString(),
    uptime_30d: 99.95,
    docker_containers: 16,
    load1: 0.42,
    days_online: 37,
    cpu_usage: 8.5,
    ram_usage: 41.2,
    disk_usage: 32.1,
    cpu_temp: 49.6
  };
}

function syntheticDocument(script) {
  return Buffer.from(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>runtime gate fixture</title></head><body><main>runtime gate fixture</main><script>${script}</script></body></html>`);
}

function createFixtureServer() {
  return createServer(async (request, response) => {
    try {
      const url = new URL(request.url || "/", "http://127.0.0.1");
      if (url.pathname === "/stats.json") {
        const body = Buffer.from(JSON.stringify(statsPayload()));
        response.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
        response.end(body);
        return;
      }
      if (url.pathname === "/api/contact-config" || url.pathname === "/api/chat-config") {
        const body = Buffer.from(JSON.stringify({ configured: false }));
        response.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
        response.end(body);
        return;
      }
      if (url.pathname === "/__lab/runtime-exception") {
        const body = syntheticDocument(`setTimeout(() => { throw new Error('LAB_RUNTIME_EXCEPTION_SELF_CHECK'); }, 0);`);
        response.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
        response.end(body);
        return;
      }
      if (url.pathname === "/__lab/unhandled-rejection") {
        const body = syntheticDocument(`Promise.reject(new Error('LAB_UNHANDLED_REJECTION_SELF_CHECK'));`);
        response.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
        response.end(body);
        return;
      }
      if (url.pathname === "/__lab/console-error") {
        const body = syntheticDocument(`console.error('LAB_CONSOLE_ERROR_SELF_CHECK');`);
        response.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
        response.end(body);
        return;
      }
      if (request.method !== "GET" && request.method !== "HEAD") {
        response.writeHead(405);
        response.end();
        return;
      }
      const target = safeStaticPath(url.pathname);
      const metadata = await stat(target);
      if (!metadata.isFile()) throw new Error("not a file");
      const body = await readFile(target);
      response.writeHead(200, {
        "Content-Type": MIME_TYPES.get(extname(target)) || "application/octet-stream",
        "Cache-Control": "no-store"
      });
      response.end(request.method === "HEAD" ? undefined : body);
    } catch (error) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end(error instanceof Error ? error.message : "not found");
    }
  });
}

async function fetchJsonWithRetry(url, options = {}, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return await response.json();
      lastError = new Error(`${response.status} ${response.statusText}`);
    } catch (error) {
      lastError = error;
    }
    await delay(100);
  }
  throw lastError || new Error(`timed out fetching ${url}`);
}

async function readChromeDebugPort(profile, timeoutMs = 20_000) {
  const activePort = join(profile, "DevToolsActivePort");
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const [portLine] = (await readFile(activePort, "utf8")).trim().split(/\r?\n/);
      if (/^[0-9]+$/.test(portLine)) return Number(portLine);
      lastError = new Error(`invalid DevToolsActivePort: ${portLine}`);
    } catch (error) {
      lastError = error;
    }
    await delay(100);
  }
  throw lastError || new Error("Chrome did not publish DevToolsActivePort");
}

async function stopProcess(child, timeoutMs = 3_000) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise((resolveExit) => child.once("exit", resolveExit));
  child.kill("SIGTERM");
  const graceful = await Promise.race([
    exited.then(() => true),
    delay(timeoutMs).then(() => false)
  ]);
  if (!graceful) {
    child.kill("SIGKILL");
    await exited;
  }
}

class CdpClient {
  constructor(webSocketUrl) {
    this.socket = new WebSocket(webSocketUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async open() {
    await new Promise((resolveOpen, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP websocket open timeout")), 10_000);
      this.socket.addEventListener("open", () => {
        clearTimeout(timer);
        resolveOpen();
      }, { once: true });
      this.socket.addEventListener("error", () => {
        clearTimeout(timer);
        reject(new Error("CDP websocket failed"));
      }, { once: true });
    });
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(message.error.message));
        else pending.resolve(message.result || {});
        return;
      }
      const callbacks = this.listeners.get(message.method);
      if (!callbacks) return;
      for (const callback of [...callbacks]) callback(message.params || {});
    });
    this.socket.addEventListener("close", () => {
      for (const pending of this.pending.values()) pending.reject(new Error("CDP websocket closed"));
      this.pending.clear();
    });
  }

  on(method, callback) {
    const callbacks = this.listeners.get(method) || new Set();
    callbacks.add(callback);
    this.listeners.set(method, callbacks);
    return () => {
      callbacks.delete(callback);
      if (callbacks.size === 0) this.listeners.delete(method);
    };
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolveSend, reject) => {
      this.pending.set(id, { resolve: resolveSend, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  waitForEvent(method, timeoutMs = 10_000) {
    return new Promise((resolveEvent, reject) => {
      const off = this.on(method, (params) => {
        clearTimeout(timer);
        off();
        resolveEvent(params);
      });
      const timer = setTimeout(() => {
        off();
        reject(new Error(`timed out waiting for ${method}`));
      }, timeoutMs);
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text || "browser evaluation failed");
    }
    return result.result?.value;
  }

  async waitFor(expression, timeoutMs = 10_000, description = expression) {
    const deadline = Date.now() + timeoutMs;
    let lastValue;
    while (Date.now() < deadline) {
      lastValue = await this.evaluate(expression);
      if (lastValue) return lastValue;
      await delay(50);
    }
    throw new Error(`timed out waiting for ${description}; last=${JSON.stringify(lastValue)}`);
  }

  async navigate(url) {
    const loaded = this.waitForEvent("Page.loadEventFired", 15_000);
    await this.send("Page.navigate", { url });
    await loaded;
  }

  close() {
    this.socket.close();
  }
}

function remoteObjectText(remoteObject) {
  if (!remoteObject) return "";
  if (Object.prototype.hasOwnProperty.call(remoteObject, "value")) return String(remoteObject.value);
  return remoteObject.description || remoteObject.unserializableValue || remoteObject.type || "";
}

function exceptionText(details) {
  const headline = details.exception?.description || details.text || "unhandled exception";
  const frame = details.stackTrace?.callFrames?.[0];
  const location = frame
    ? `${frame.url || details.url || "<anonymous>"}:${frame.lineNumber + 1}:${frame.columnNumber + 1}`
    : `${details.url || "<anonymous>"}:${details.lineNumber + 1}:${details.columnNumber + 1}`;
  return `${headline} @ ${location}`;
}

function consoleText(event) {
  const text = event.args.map(remoteObjectText).filter(Boolean).join(" ") || `<console.${event.type}>`;
  const frame = event.stackTrace?.callFrames?.[0];
  const location = frame ? ` @ ${frame.url || "<anonymous>"}:${frame.lineNumber + 1}:${frame.columnNumber + 1}` : "";
  return `console.${event.type}: ${text}${location}`;
}

class RuntimeFailureGate {
  constructor(cdp) {
    this.cdp = cdp;
    this.exceptions = new Map();
    this.consoleFailures = [];
    this.unsubscribe = [];
  }

  start() {
    this.unsubscribe.push(
      this.cdp.on("Runtime.exceptionThrown", ({ exceptionDetails }) => {
        this.exceptions.set(exceptionDetails.exceptionId, exceptionText(exceptionDetails));
      }),
      this.cdp.on("Runtime.exceptionRevoked", ({ exceptionId }) => {
        this.exceptions.delete(exceptionId);
      }),
      this.cdp.on("Runtime.consoleAPICalled", (event) => {
        if (HIGH_SEVERITY_CONSOLE_TYPES.has(event.type)) this.consoleFailures.push(consoleText(event));
      })
    );
  }

  stop() {
    for (const off of this.unsubscribe.splice(0)) off();
  }

  snapshot() {
    return {
      exceptions: [...this.exceptions.values()],
      consoleFailures: [...this.consoleFailures]
    };
  }

  assertClean(context) {
    const snapshot = this.snapshot();
    assert.deepEqual(
      snapshot,
      { exceptions: [], consoleFailures: [] },
      `${context}: browser runtime failures ${JSON.stringify(snapshot)}`
    );
  }
}

async function openPage(debugPort, width, height) {
  const target = await fetchJsonWithRetry(
    `http://127.0.0.1:${debugPort}/json/new?about:blank`,
    { method: "PUT" }
  );
  const cdp = new CdpClient(target.webSocketDebuggerUrl);
  await cdp.open();
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Network.enable");
  await cdp.send("Network.setBlockedURLs", {
    urls: ["*://static.cloudflareinsights.com/*", "*://cloudflareinsights.com/*"]
  });
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false
  });
  return cdp;
}

async function waitForScenario(cdp, scenario) {
  await cdp.waitFor(
    `document.readyState === "complete" && document.documentElement.lang === ${JSON.stringify(scenario.language)}`,
    10_000,
    `${scenario.path} ${scenario.width}px document initialization`
  );
  if (scenario.kind === "main") {
    await cdp.waitFor(
      `document.querySelector('#liveDot')?.dataset.state === "live" && document.querySelector('[data-stat="docker_containers"]')?.textContent === "16"`,
      10_000,
      `${scenario.path} ${scenario.width}px live statistics`
    );
  } else if (scenario.kind === "proof") {
    await cdp.waitFor(
      `document.querySelectorAll('[data-proof-project-id]').length === 3`,
      10_000,
      `${scenario.path} ${scenario.width}px proof initialization`
    );
  } else {
    await cdp.waitFor(
      `document.querySelector('#demoDate')?.textContent?.trim().length > 0`,
      10_000,
      `${scenario.path} ${scenario.width}px smart-home initialization`
    );
  }
  await delay(RUNTIME_SETTLE_MS);
}

function expectGateFailure(gate, context, marker) {
  let detected;
  try {
    gate.assertClean(context);
  } catch (error) {
    detected = error;
  }
  assert.ok(detected instanceof Error, `${context}: runtime gate did not reject synthetic failure`);
  assert.match(detected.message, new RegExp(marker), `${context}: diagnostic did not include failure marker`);
}

async function runSelfCheck(debugPort, baseUrl, path, marker, passMarker) {
  const cdp = await openPage(debugPort, 1280, 900);
  const gate = new RuntimeFailureGate(cdp);
  gate.start();
  try {
    await cdp.navigate(`${baseUrl}${path}`);
    await delay(RUNTIME_SETTLE_MS);
    expectGateFailure(gate, `${path} 1280px synthetic self-check`, marker);
    console.log(`${passMarker}=PASS`);
  } finally {
    gate.stop();
    cdp.close();
  }
}

async function runCleanScenario(debugPort, baseUrl, scenario) {
  const cdp = await openPage(debugPort, scenario.width, scenario.height);
  const gate = new RuntimeFailureGate(cdp);
  gate.start();
  const context = `${scenario.path} ${scenario.width}px`;
  try {
    await cdp.navigate(`${baseUrl}${scenario.path}`);
    await waitForScenario(cdp, scenario);
    gate.assertClean(context);
    console.log(`LAB_RUNTIME_CLEAN ${context}`);
  } finally {
    gate.stop();
    cdp.close();
  }
}

async function runRuntimeGate(baseUrl) {
  const profile = await mkdtemp(join(tmpdir(), "rozkalns-cv-runtime-gate-chrome-"));
  const chrome = spawn(CHROME_BIN, [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-first-run",
    "--lang=en-US",
    "--remote-debugging-port=0",
    `--user-data-dir=${profile}`,
    "about:blank"
  ], { stdio: ["ignore", "pipe", "pipe"] });
  let stderr = "";
  chrome.stderr.on("data", (chunk) => { stderr += chunk.toString(); });

  try {
    const debugPort = await readChromeDebugPort(profile);
    await fetchJsonWithRetry(`http://127.0.0.1:${debugPort}/json/version`);

    await runSelfCheck(
      debugPort,
      baseUrl,
      "/__lab/runtime-exception",
      "LAB_RUNTIME_EXCEPTION_SELF_CHECK",
      "LAB_RUNTIME_EXCEPTION_DETECTOR"
    );
    await runSelfCheck(
      debugPort,
      baseUrl,
      "/__lab/unhandled-rejection",
      "LAB_UNHANDLED_REJECTION_SELF_CHECK",
      "LAB_UNHANDLED_REJECTION_DETECTOR"
    );
    await runSelfCheck(
      debugPort,
      baseUrl,
      "/__lab/console-error",
      "LAB_CONSOLE_ERROR_SELF_CHECK",
      "LAB_CONSOLE_ERROR_DETECTOR"
    );

    for (const scenario of CLEAN_MATRIX) {
      await runCleanScenario(debugPort, baseUrl, scenario);
    }
    console.log(`LAB_RUNTIME_CLEAN_SURFACES=PASS scenarios=${CLEAN_MATRIX.length}`);
  } catch (error) {
    throw new Error(`${error instanceof Error ? error.stack : error}\nChrome stderr:\n${stderr.slice(-4000)}`);
  } finally {
    await stopProcess(chrome);
    await rm(profile, {
      recursive: true,
      force: true,
      maxRetries: 5,
      retryDelay: 100
    });
  }
}

const server = createFixtureServer();
try {
  const address = await listen(server);
  await runRuntimeGate(`http://127.0.0.1:${address.port}`);
  console.log("BROWSER_RUNTIME_ERRORS=PASS");
} finally {
  await closeServer(server);
}
