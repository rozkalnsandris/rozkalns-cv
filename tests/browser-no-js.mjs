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
  [".webp", "image/webp"],
  [".pdf", "application/pdf"]
]);

const PDF_BY_LANGUAGE = Object.freeze({
  en: "/cv.pdf",
  de: "/cv-de.pdf",
  lv: "/cv-lv.pdf"
});

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
      const url = new URL(request.url || "/", "http://127.0.0.1");
      if (["/stats.json", "/api/contact-config", "/api/chat-config"].includes(url.pathname)) {
        state.dynamicRequests.push(url.pathname);
        response.writeHead(503, { "Content-Type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ configured: false }));
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

  async navigate(url) {
    const loaded = this.waitForEvent("Page.loadEventFired", 15_000);
    await this.send("Page.navigate", { url });
    await loaded;
  }

  close() {
    this.socket.close();
  }
}

async function documentRoot(cdp) {
  const { root } = await cdp.send("DOM.getDocument", { depth: 1, pierce: true });
  return root.nodeId;
}

async function queryNode(cdp, selector) {
  const nodeId = (await cdp.send("DOM.querySelector", {
    nodeId: await documentRoot(cdp),
    selector
  })).nodeId;
  assert.ok(nodeId, `missing no-JS selector: ${selector}`);
  return nodeId;
}

async function attributes(cdp, nodeId) {
  const raw = (await cdp.send("DOM.getAttributes", { nodeId })).attributes || [];
  const result = new Map();
  for (let index = 0; index < raw.length; index += 2) result.set(raw[index], raw[index + 1]);
  return result;
}

async function outerHtml(cdp, nodeId) {
  return (await cdp.send("DOM.getOuterHTML", { nodeId })).outerHTML || "";
}

async function computedStyle(cdp, nodeId) {
  const rows = (await cdp.send("CSS.getComputedStyleForNode", { nodeId })).computedStyle || [];
  return new Map(rows.map(({ name, value }) => [name, value]));
}

function assertVisible(style, context) {
  assert.notEqual(style.get("display"), "none", `${context}: display:none`);
  assert.notEqual(style.get("visibility"), "hidden", `${context}: visibility:hidden`);
  assert.notEqual(style.get("visibility"), "collapse", `${context}: visibility:collapse`);
}

function assertHidden(style, context) {
  assert.equal(style.get("display"), "none", `${context}: JS-only control must be hidden when scripting is disabled`);
}

async function assertVisibleContent(cdp, selector, minMarkupLength, context) {
  const nodeId = await queryNode(cdp, selector);
  assertVisible(await computedStyle(cdp, nodeId), context);
  const markup = await outerHtml(cdp, nodeId);
  assert.ok(markup.length >= minMarkupLength, `${context}: recruiter markup too small (${markup.length})`);
  return { nodeId, markup };
}

async function assertLink(cdp, selector, expectedHref, context) {
  const nodeId = await queryNode(cdp, selector);
  assertVisible(await computedStyle(cdp, nodeId), context);
  const attrs = await attributes(cdp, nodeId);
  assert.equal(attrs.get("href"), expectedHref, `${context}: unexpected href`);
}

async function runNoJsLab(baseUrl, state) {
  const profile = await mkdtemp(join(tmpdir(), "rozkalns-cv-no-js-chrome-"));
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
  let targetId;
  let debugPort;
  try {
    debugPort = await readChromeDebugPort(profile);
    await fetchJsonWithRetry(`http://127.0.0.1:${debugPort}/json/version`);
    const target = await fetchJsonWithRetry(
      `http://127.0.0.1:${debugPort}/json/new?about:blank`,
      { method: "PUT" }
    );
    targetId = target.id;
    cdp = new CdpClient(target.webSocketDebuggerUrl);
    await cdp.open();
    await cdp.send("Page.enable");
    await cdp.send("DOM.enable");
    await cdp.send("CSS.enable");
    await cdp.send("Emulation.setScriptExecutionDisabled", { value: true });

    const matrix = [
      { width: 1280, height: 900, language: "en" },
      { width: 390, height: 844, language: "en" },
      { width: 1280, height: 900, language: "de" },
      { width: 390, height: 844, language: "de" },
      { width: 1280, height: 900, language: "lv" },
      { width: 390, height: 844, language: "lv" }
    ];

    for (const scenario of matrix) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: scenario.width,
        height: scenario.height,
        deviceScaleFactor: 1,
        mobile: false
      });
      const path = `/${scenario.language}/`;
      await cdp.navigate(`${baseUrl}${path}`);

      const htmlNode = await queryNode(cdp, "html");
      const htmlAttrs = await attributes(cdp, htmlNode);
      assert.equal(htmlAttrs.get("lang"), scenario.language, `${path}: localized lang attribute`);

      const identity = await assertVisibleContent(cdp, "h1", 8, `${path} identity`);
      assert.ok(identity.markup.includes("Andris Rožkalns"), `${path}: identity must remain server-rendered`);
      const role = await assertVisibleContent(cdp, ".role", 8, `${path} role`);
      assert.ok(role.markup.includes("Technical Support") && role.markup.includes("Linux Operations"), `${path}: current support/operations role must remain server-rendered`);
      await assertVisibleContent(cdp, "#projects", 220, `${path} projects`);
      await assertVisibleContent(cdp, "#skills", 120, `${path} skills`);
      await assertVisibleContent(cdp, "#experience", 180, `${path} experience`);

      await assertLink(cdp, "#pdfLink", PDF_BY_LANGUAGE[scenario.language], `${path} PDF action`);
      const githubNode = await queryNode(cdp, ".actions a[href*='github.com']");
      assertVisible(await computedStyle(cdp, githubNode), `${path} GitHub action`);
      await assertLink(cdp, "#proofLink", `/${scenario.language}/proof/`, `${path} engineering proof action`);

      assertHidden(await computedStyle(cdp, await queryNode(cdp, "#contactReveal")), `${path} contact verification`);
      assertHidden(await computedStyle(cdp, await queryNode(cdp, "#chatLauncher")), `${path} CV assistant launcher`);
      assertHidden(await computedStyle(cdp, await queryNode(cdp, "#chatBackdrop")), `${path} CV assistant dialog`);

      console.log(`LAB_NO_JS ${scenario.language} ${scenario.width}px recruiter_content=PASS static_actions=PASS js_only_controls=HIDDEN`);
    }

    assert.deepEqual(state.dynamicRequests, [], `no-JS path unexpectedly requested dynamic APIs: ${JSON.stringify(state.dynamicRequests)}`);
    console.log("LAB_NO_JS_RECRUITER_PATH=PASS");
  } catch (error) {
    throw new Error(`${error instanceof Error ? error.stack : error}\nChrome stderr:\n${stderr.slice(-4000)}`);
  } finally {
    cdp?.close();
    if (debugPort && targetId) {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json/close/${encodeURIComponent(targetId)}`);
      if (!response.ok && response.status !== 404) {
        throw new Error(`failed to close Chromium target ${targetId}: ${response.status} ${response.statusText}`);
      }
    }
    await stopProcess(chrome);
    await rm(profile, {
      recursive: true,
      force: true,
      maxRetries: 5,
      retryDelay: 100
    });
  }
}

const state = { dynamicRequests: [] };
const server = createFixtureServer(state);
try {
  const address = await listen(server);
  await runNoJsLab(`http://127.0.0.1:${address.port}`, state);
  console.log("BROWSER_NO_JS=PASS");
} finally {
  await closeServer(server);
}
