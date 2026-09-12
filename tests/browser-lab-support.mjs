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
const MAX_SUPPORT_CLS = 0.05;

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

const MATRIX = [
  { kind: "proof", path: "/en/proof/", language: "en", width: 1280, height: 900, maxRequests: 5, maxBytes: 56 * 1024 },
  { kind: "proof", path: "/en/proof/", language: "en", width: 390, height: 844, maxRequests: 5, maxBytes: 56 * 1024 },
  { kind: "proof", path: "/de/proof/", language: "de", width: 1280, height: 900, maxRequests: 5, maxBytes: 56 * 1024 },
  { kind: "proof", path: "/de/proof/", language: "de", width: 390, height: 844, maxRequests: 5, maxBytes: 56 * 1024 },
  { kind: "proof", path: "/lv/proof/", language: "lv", width: 1280, height: 900, maxRequests: 5, maxBytes: 56 * 1024 },
  { kind: "proof", path: "/lv/proof/", language: "lv", width: 390, height: 844, maxRequests: 5, maxBytes: 56 * 1024 },
  { kind: "smarthome", path: "/smarthome.html", language: "en", width: 1280, height: 900, maxRequests: 7, maxBytes: 96 * 1024 },
  { kind: "smarthome", path: "/smarthome.html", language: "en", width: 390, height: 844, maxRequests: 7, maxBytes: 96 * 1024 }
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

function createFixtureServer(state) {
  return createServer(async (request, response) => {
    try {
      if (request.method !== "GET" && request.method !== "HEAD") {
        response.writeHead(405);
        response.end();
        return;
      }
      const url = new URL(request.url || "/", "http://127.0.0.1");
      const target = safeStaticPath(url.pathname);
      const metadata = await stat(target);
      if (!metadata.isFile()) throw new Error("not a file");
      const body = await readFile(target);
      state.staticRequests.push({ path: url.pathname, bytes: body.length });
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
      const callbacks = this.listeners.get(method) || new Set();
      const onEvent = (params) => {
        clearTimeout(timer);
        callbacks.delete(onEvent);
        resolveEvent(params);
      };
      const timer = setTimeout(() => {
        callbacks.delete(onEvent);
        reject(new Error(`timed out waiting for ${method}`));
      }, timeoutMs);
      callbacks.add(onEvent);
      this.listeners.set(method, callbacks);
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true
    });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.text || "browser evaluation failed");
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

const LAYOUT_OBSERVER_SOURCE = `(() => {
  globalThis.__supportLayoutObserverSupported = PerformanceObserver.supportedEntryTypes?.includes('layout-shift') === true;
  globalThis.__supportLayoutShifts = [];
  if (!globalThis.__supportLayoutObserverSupported) return;
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) globalThis.__supportLayoutShifts.push(entry.value);
    }
  });
  observer.observe({ type: 'layout-shift', buffered: true });
  globalThis.__supportLayoutObserver = observer;
})();`;

async function readSurfaceState(cdp) {
  await cdp.evaluate(`document.fonts ? document.fonts.ready.then(() => true) : true`);
  await cdp.evaluate(`new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))`);
  await delay(50);
  return await cdp.evaluate(`(() => {
    const skip = document.querySelector('.skip-link');
    const skipTarget = skip?.getAttribute('href') || '';
    const targetExists = skipTarget.startsWith('#') && document.querySelector(skipTarget) !== null;
    return {
      lang: document.documentElement.lang,
      h1Count: document.querySelectorAll('h1').length,
      h1Text: document.querySelector('h1')?.textContent?.trim() || '',
      mainCount: document.querySelectorAll('main').length,
      skipTargetExists: targetExists,
      overflowPx: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
      clsSupported: globalThis.__supportLayoutObserverSupported === true,
      cls: (globalThis.__supportLayoutShifts || []).reduce((sum, value) => sum + value, 0),
      stylesLoaded: [...document.styleSheets].some((sheet) => sheet.href && /\\/assets\\/styles\\.[0-9a-f]{12}\\.css$/.test(new URL(sheet.href).pathname)),
      proofProjects: document.querySelectorAll('[data-proof-project-id]').length,
      proofEvidenceLinks: document.querySelectorAll('.proof-evidence-link').length,
      smartDevices: document.querySelectorAll('.demo-device').length,
      smartLanguageButtons: document.querySelectorAll('.language-switcher button[data-lang]').length,
      smartActiveLanguages: document.querySelectorAll('.language-switcher button[aria-pressed="true"]').length,
      smartDate: document.querySelector('#demoDate')?.textContent?.trim() || ''
    };
  })()`);
}

function assertResourceBudget(requests, scenario, context) {
  const totalBytes = requests.reduce((sum, item) => sum + item.bytes, 0);
  assert.ok(
    requests.length <= scenario.maxRequests,
    `${context}: static request count ${requests.length} > ${scenario.maxRequests}; requests=${JSON.stringify(requests)}`
  );
  assert.ok(
    totalBytes <= scenario.maxBytes,
    `${context}: static bytes ${totalBytes} > ${scenario.maxBytes}; requests=${JSON.stringify(requests)}`
  );
  const paths = requests.map((item) => item.path);
  assert.ok(paths.includes(scenario.path), `${context}: route document was not loaded; paths=${JSON.stringify(paths)}`);
  assert.ok(
    paths.some((path) => /^\/assets\/styles\.[0-9a-f]{12}\.css$/.test(path)),
    `${context}: stylesheet asset missing; paths=${JSON.stringify(paths)}`
  );
  if (scenario.kind === "smarthome") {
    assert.ok(
      paths.some((path) => /^\/assets\/smarthome\.[0-9a-f]{12}\.mjs$/.test(path)),
      `${context}: smart-home module missing; paths=${JSON.stringify(paths)}`
    );
    assert.ok(
      paths.some((path) => /^\/assets\/i18n\.[0-9a-f]{12}\.mjs$/.test(path)),
      `${context}: i18n module missing; paths=${JSON.stringify(paths)}`
    );
  }
  return { requests: requests.length, bytes: totalBytes };
}

function assertSurfaceState(result, scenario, context) {
  assert.equal(result.lang, scenario.language, `${context}: unexpected document language`);
  assert.equal(result.h1Count, 1, `${context}: expected exactly one h1`);
  assert.ok(result.h1Text, `${context}: h1 is empty`);
  assert.equal(result.mainCount, 1, `${context}: expected exactly one main landmark`);
  assert.equal(result.skipTargetExists, true, `${context}: skip-link target missing`);
  assert.equal(result.stylesLoaded, true, `${context}: generated stylesheet not loaded`);
  assert.ok(result.overflowPx <= 1, `${context}: horizontal overflow ${result.overflowPx}px`);
  assert.equal(result.clsSupported, true, `${context}: layout-shift observer unavailable`);
  assert.ok(result.cls <= MAX_SUPPORT_CLS, `${context}: synthetic CLS ${result.cls.toFixed(6)} > ${MAX_SUPPORT_CLS}`);

  if (scenario.kind === "proof") {
    assert.equal(result.proofProjects, 3, `${context}: expected three proof projects`);
    assert.ok(result.proofEvidenceLinks >= 6, `${context}: expected public evidence links`);
  } else {
    assert.equal(result.smartDevices, 8, `${context}: expected eight smart-home device cards`);
    assert.equal(result.smartLanguageButtons, 3, `${context}: expected three language controls`);
    assert.equal(result.smartActiveLanguages, 1, `${context}: expected one active language control`);
    assert.ok(result.smartDate, `${context}: smart-home module did not populate demo date`);
  }
}

async function runSupportingSurfaceLab(baseUrl, state) {
  const profile = await mkdtemp(join(tmpdir(), "rozkalns-cv-support-lab-chrome-"));
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

  let cdp;
  try {
    const debugPort = await readChromeDebugPort(profile);
    await fetchJsonWithRetry(`http://127.0.0.1:${debugPort}/json/version`);
    const target = await fetchJsonWithRetry(
      `http://127.0.0.1:${debugPort}/json/new?about:blank`,
      { method: "PUT" }
    );
    cdp = new CdpClient(target.webSocketDebuggerUrl);
    await cdp.open();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Network.enable");
    await cdp.send("Network.setBlockedURLs", {
      urls: ["*://static.cloudflareinsights.com/*", "*://cloudflareinsights.com/*"]
    });
    await cdp.send("Page.addScriptToEvaluateOnNewDocument", { source: LAYOUT_OBSERVER_SOURCE });

    for (const scenario of MATRIX) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: scenario.width,
        height: scenario.height,
        deviceScaleFactor: 1,
        mobile: false
      });
      state.staticRequests.length = 0;
      await cdp.navigate(`${baseUrl}${scenario.path}`);
      await cdp.waitFor(
        `document.readyState === "complete" && document.documentElement.lang === ${JSON.stringify(scenario.language)}`,
        10_000,
        `${scenario.path} ${scenario.width}px initialization`
      );
      if (scenario.kind === "smarthome") {
        await cdp.waitFor(
          `document.querySelector('#demoDate')?.textContent?.trim().length > 0`,
          10_000,
          `${scenario.path} ${scenario.width}px module initialization`
        );
      }
      const result = await readSurfaceState(cdp);
      const context = `${scenario.path} ${scenario.width}px`;
      assertSurfaceState(result, scenario, context);
      const resources = assertResourceBudget([...state.staticRequests], scenario, context);
      console.log(
        `LAB_SUPPORT_SURFACE ${context} cls=${result.cls.toFixed(6)} overflow=${result.overflowPx} requests=${resources.requests} bytes=${resources.bytes}`
      );
    }
    console.log("LAB_SUPPORT_SURFACES=PASS");
  } catch (error) {
    throw new Error(`${error instanceof Error ? error.stack : error}\nChrome stderr:\n${stderr.slice(-4000)}`);
  } finally {
    cdp?.close();
    await stopProcess(chrome);
    await rm(profile, {
      recursive: true,
      force: true,
      maxRetries: 5,
      retryDelay: 100
    });
  }
}

const state = { staticRequests: [] };
const server = createFixtureServer(state);
try {
  const address = await listen(server);
  await runSupportingSurfaceLab(`http://127.0.0.1:${address.port}`, state);
  console.log("BROWSER_LAB_SUPPORT_STABILITY=PASS");
} finally {
  await closeServer(server);
}
