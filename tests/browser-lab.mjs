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
const MAX_SYNTHETIC_CLS = 0.05;
const MAX_INITIAL_STATIC_REQUESTS = 10;
const MAX_INITIAL_STATIC_BYTES = 120 * 1024;

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

function createFixtureServer(state) {
  return createServer(async (request, response) => {
    try {
      const url = new URL(request.url || "/", "http://127.0.0.1");
      if (url.pathname === "/stats.json") {
        await delay(state.statsDelayMs);
        const body = Buffer.from(JSON.stringify(statsPayload()));
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(body);
        return;
      }
      if (url.pathname === "/api/contact-config" || url.pathname === "/api/chat-config") {
        const body = Buffer.from(JSON.stringify({ configured: false }));
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
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
    this.socket.addEventListener("close", () => {
      for (const pending of this.pending.values()) {
        pending.reject(new Error("CDP websocket closed"));
      }
      this.pending.clear();
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
  globalThis.__labLayoutObserverSupported = PerformanceObserver.supportedEntryTypes?.includes('layout-shift') === true;
  globalThis.__labLayoutShifts = [];
  if (!globalThis.__labLayoutObserverSupported) return;
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.hadRecentInput) continue;
      globalThis.__labLayoutShifts.push({
        value: entry.value,
        startTime: entry.startTime,
        sources: (entry.sources || []).slice(0, 5).map((source) => {
          const node = source.node;
          return {
            tag: node?.tagName || '',
            id: node?.id || '',
            className: typeof node?.className === 'string' ? node.className : '',
            previous: source.previousRect ? {
              x: source.previousRect.x,
              y: source.previousRect.y,
              width: source.previousRect.width,
              height: source.previousRect.height
            } : null,
            current: source.currentRect ? {
              x: source.currentRect.x,
              y: source.currentRect.y,
              width: source.currentRect.width,
              height: source.currentRect.height
            } : null
          };
        })
      });
    }
  });
  observer.observe({ type: 'layout-shift', buffered: true });
  globalThis.__labLayoutObserver = observer;
})();`;

async function settleAndReadLayout(cdp) {
  await cdp.evaluate(`document.fonts ? document.fonts.ready.then(() => true) : true`);
  await cdp.evaluate(`new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))`);
  await delay(50);
  return await cdp.evaluate(`(() => {
    const entries = globalThis.__labLayoutShifts || [];
    const photo = document.querySelector('.profile-photo');
    return {
      supported: globalThis.__labLayoutObserverSupported === true,
      score: entries.reduce((sum, entry) => sum + entry.value, 0),
      entries,
      photo: photo ? {
        width: photo.getAttribute('width'),
        height: photo.getAttribute('height'),
        naturalWidth: photo.naturalWidth,
        naturalHeight: photo.naturalHeight
      } : null
    };
  })()`);
}

function assertLayoutBudget(result, context) {
  assert.equal(result.supported, true, `${context}: layout-shift observer unavailable`);
  assert.ok(result.photo, `${context}: profile photo missing`);
  assert.equal(result.photo.width, "118", `${context}: profile photo width reservation`);
  assert.equal(result.photo.height, "118", `${context}: profile photo height reservation`);
  assert.ok(result.photo.naturalWidth > 0 && result.photo.naturalHeight > 0, `${context}: profile photo failed to load`);
  assert.ok(
    result.score <= MAX_SYNTHETIC_CLS,
    `${context}: synthetic CLS ${result.score.toFixed(6)} > ${MAX_SYNTHETIC_CLS}; shifts=${JSON.stringify(result.entries)}`
  );
}

function assertInitialResourceShape(requests) {
  const totalBytes = requests.reduce((sum, item) => sum + item.bytes, 0);
  const paths = requests.map((item) => item.path);
  const largest = [...requests].sort((a, b) => b.bytes - a.bytes).slice(0, 8);
  assert.ok(
    requests.length <= MAX_INITIAL_STATIC_REQUESTS,
    `initial synthetic static request count ${requests.length} > ${MAX_INITIAL_STATIC_REQUESTS}; requests=${JSON.stringify(requests)}`
  );
  assert.ok(
    totalBytes <= MAX_INITIAL_STATIC_BYTES,
    `initial synthetic static bytes ${totalBytes} > ${MAX_INITIAL_STATIC_BYTES}; largest=${JSON.stringify(largest)}`
  );
  for (const pattern of [
    /^\/en\/$/,
    /^\/assets\/app\.[0-9a-f]{12}\.mjs$/,
    /^\/assets\/i18n\.[0-9a-f]{12}\.mjs$/,
    /^\/assets\/i18n\.[0-9a-f]{12}\.css$/,
    /^\/assets\/photo\.[0-9a-f]{12}\.webp$/,
    /^\/i18n\/en\.[0-9a-f]{12}\.json$/
  ]) {
    assert.ok(paths.some((path) => pattern.test(path)), `initial synthetic loading shape missing ${pattern}; paths=${JSON.stringify(paths)}`);
  }
  return { requests: requests.length, bytes: totalBytes, largest };
}

async function runBrowserLab(baseUrl, state) {
  const profile = await mkdtemp(join(tmpdir(), "rozkalns-cv-lab-chrome-"));
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

    const matrix = [
      { width: 1280, height: 900, path: "/en/", language: "en" },
      { width: 390, height: 844, path: "/en/", language: "en" },
      { width: 1280, height: 900, path: "/de/", language: "de" },
      { width: 390, height: 844, path: "/de/", language: "de" },
      { width: 1280, height: 900, path: "/lv/", language: "lv" },
      { width: 390, height: 844, path: "/lv/", language: "lv" }
    ];

    let initialResourceResult;
    for (const [index, scenario] of matrix.entries()) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: scenario.width,
        height: scenario.height,
        deviceScaleFactor: 1,
        mobile: false
      });
      if (index === 0) state.staticRequests.length = 0;
      await cdp.navigate(`${baseUrl}${scenario.path}`);
      await cdp.waitFor(
        `document.readyState === "complete" && document.documentElement.lang === ${JSON.stringify(scenario.language)}`,
        10_000,
        `${scenario.language} ${scenario.width}px document initialization`
      );
      await cdp.waitFor(
        `document.querySelector('#liveDot')?.dataset.state === "live" && document.querySelector('[data-stat="docker_containers"]')?.textContent === "16"`,
        10_000,
        `${scenario.language} ${scenario.width}px delayed live statistics`
      );
      const layout = await settleAndReadLayout(cdp);
      const context = `${scenario.language} ${scenario.width}px`;
      assertLayoutBudget(layout, context);
      console.log(`LAB_SYNTHETIC_LAYOUT ${context} cls=${layout.score.toFixed(6)} entries=${layout.entries.length}`);
      if (index === 0) {
        initialResourceResult = assertInitialResourceShape([...state.staticRequests]);
        console.log(`LAB_SYNTHETIC_LOADING static_requests=${initialResourceResult.requests} static_bytes=${initialResourceResult.bytes}`);
      }
    }

    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false
    });
    await cdp.navigate(`${baseUrl}/en/`);
    await cdp.waitFor(
      `document.querySelector('#liveDot')?.dataset.state === "live"`,
      10_000,
      "synthetic detector self-check baseline"
    );
    await settleAndReadLayout(cdp);
    await cdp.evaluate(`globalThis.__labLayoutShifts.length = 0`);
    await cdp.evaluate(`(() => {
      const regression = document.createElement('div');
      regression.id = 'synthetic-layout-regression';
      regression.setAttribute('aria-hidden', 'true');
      regression.style.cssText = 'height:180px;width:100%;display:block';
      document.body.prepend(regression);
    })()`);
    const detectorCheck = await settleAndReadLayout(cdp);
    assert.ok(
      detectorCheck.score > MAX_SYNTHETIC_CLS,
      `synthetic regression detector did not trip; score=${detectorCheck.score}; shifts=${JSON.stringify(detectorCheck.entries)}`
    );
    console.log(`LAB_SYNTHETIC_REGRESSION_DETECTOR=PASS cls=${detectorCheck.score.toFixed(6)}`);
    console.log("LAB_SYNTHETIC_NOT_FIELD_CWV=PASS");
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

const state = {
  statsDelayMs: 300,
  staticRequests: []
};
const server = createFixtureServer(state);
try {
  const address = await listen(server);
  await runBrowserLab(`http://127.0.0.1:${address.port}`, state);
  console.log("BROWSER_LAB_STABILITY=PASS");
} finally {
  await closeServer(server);
}
