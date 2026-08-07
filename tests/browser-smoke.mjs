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

if (!CHROME_BIN) {
  throw new Error("CHROME_BIN is required");
}
if (typeof WebSocket !== "function") {
  throw new Error("This test requires the Node.js WebSocket implementation");
}

const MIME_TYPES = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".pdf", "application/pdf"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"]
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

function readRequestBody(request) {
  return new Promise((resolveBody, reject) => {
    const chunks = [];
    let size = 0;
    request.on("data", (chunk) => {
      size += chunk.length;
      if (size > 64 * 1024) {
        reject(new Error("request fixture exceeded size limit"));
        request.destroy();
        return;
      }
      chunks.push(chunk);
    });
    request.on("end", () => resolveBody(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

function safeStaticPath(pathname) {
  const decoded = decodeURIComponent(pathname === "/" ? "/index.html" : pathname);
  const relative = normalize(decoded).replace(/^([/\\])+/, "");
  const target = resolve(HTML_ROOT, relative);
  if (target !== HTML_ROOT && !target.startsWith(`${HTML_ROOT}${sep}`)) {
    throw new Error("unsafe fixture path");
  }
  return target;
}

function statsPayload(mode) {
  const updated = mode === "stale"
    ? new Date(Date.now() - 20 * 60 * 1000).toISOString()
    : new Date().toISOString();
  const payload = {
    updated,
    uptime_30d: 99.95,
    docker_containers: 16,
    load1: 0.42,
    days_online: 37,
    cpu_usage: 8.5,
    ram_usage: 41.2,
    disk_usage: 32.1,
    cpu_temp: 49.6
  };
  if (mode === "invalid") payload.cpu_usage = "not-a-number";
  return payload;
}

function createFixtureServer(state) {
  return createServer(async (request, response) => {
    try {
      const url = new URL(request.url || "/", "http://127.0.0.1");
      if (url.pathname === "/stats.json") {
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(JSON.stringify(statsPayload(state.statsMode)));
        return;
      }

      if (url.pathname === "/api/chat" && request.method === "POST") {
        const body = JSON.parse(await readRequestBody(request));
        state.chatRequests.push(body);
        if (body.message === "Trigger failure") {
          response.writeHead(503, {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store"
          });
          response.end(JSON.stringify({ reply: "Synthetic chat failure" }));
          return;
        }
        response.writeHead(200, {
          "Content-Type": "text/plain; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.write("Browser ");
        await delay(20);
        response.end("reply");
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

async function reservePort() {
  const server = createServer();
  const address = await listen(server);
  const port = address.port;
  await closeServer(server);
  return port;
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
      const timer = setTimeout(() => {
        callbacks.delete(onEvent);
        reject(new Error(`timed out waiting for ${method}`));
      }, timeoutMs);
      const callbacks = this.listeners.get(method) || new Set();
      const onEvent = (params) => {
        clearTimeout(timer);
        callbacks.delete(onEvent);
        resolveEvent(params);
      };
      callbacks.add(onEvent);
      this.listeners.set(method, callbacks);
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
      userGesture: true
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

  async key(key, modifiers = 0) {
    await this.send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key,
      code: key,
      modifiers
    });
    await this.send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key,
      code: key,
      modifiers
    });
  }

  close() {
    this.socket.close();
  }
}

async function runBrowserSmoke(baseUrl, state) {
  const debugPort = await reservePort();
  const profile = await mkdtemp(join(tmpdir(), "rozkalns-cv-chrome-"));
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
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${profile}`,
    "about:blank"
  ], { stdio: ["ignore", "pipe", "pipe"] });
  let stderr = "";
  chrome.stderr.on("data", (chunk) => { stderr += chunk.toString(); });

  let cdp;
  try {
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

    await cdp.navigate(`${baseUrl}/`);
    await cdp.waitFor(
      `document.readyState === "complete" && document.documentElement.lang === "en"`,
      10_000,
      "English document initialization"
    );
    await cdp.waitFor(
      `document.querySelector("#liveDot")?.dataset.state === "live" && document.querySelector('[data-stat="docker_containers"]')?.textContent === "16"`,
      10_000,
      "live statistics rendering"
    );

    const initialContract = await cdp.evaluate(`(() => ({
      role: document.querySelector('[data-i18n="role"]')?.textContent,
      pdf: document.querySelector('#pdfLink')?.getAttribute('href'),
      dialogModal: document.querySelector('#chatDialog')?.getAttribute('aria-modal'),
      privacy: document.querySelector('[data-i18n="chat_privacy"]')?.textContent
    }))()`);
    assert.equal(initialContract.role, "Junior DevOps & Linux Engineer");
    assert.equal(initialContract.pdf, "/cv.pdf");
    assert.equal(initialContract.dialogModal, "true");
    assert.match(initialContract.privacy, /raw IP addresses are not stored/i);

    await cdp.evaluate(`document.querySelector('[data-lang="lv"]').click()`);
    await cdp.waitFor(
      `document.documentElement.lang === "lv" && document.querySelector('#pdfLink')?.getAttribute('href') === "/cv-lv.pdf"`,
      10_000,
      "Latvian language switch"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('[data-i18n="role"]').textContent`),
      "Junior DevOps un Linux inženieris"
    );

    await cdp.evaluate(`document.querySelector('#chatLauncher').click()`);
    await cdp.waitFor(
      `document.querySelector('#chatBackdrop').hidden === false && document.activeElement?.id === "chatInput" && document.querySelector('#pageShell').inert === true`,
      5_000,
      "accessible dialog focus"
    );
    await cdp.evaluate(`document.querySelector('#chatClose').focus()`);
    await cdp.key("Tab", 8);
    assert.equal(await cdp.evaluate(`document.activeElement?.id`), "chatSend");
    await cdp.key("Escape");
    await cdp.waitFor(
      `document.querySelector('#chatBackdrop').hidden === true && document.activeElement?.id === "chatLauncher" && document.querySelector('#pageShell').inert === false`,
      5_000,
      "Escape dialog dismissal"
    );

    await cdp.evaluate(`document.querySelector('#chatLauncher').click()`);
    await cdp.waitFor(`document.activeElement?.id === "chatInput"`, 5_000, "chat input focus");

    async function submit(message, expectedStatus) {
      await cdp.evaluate(`(() => {
        const input = document.querySelector('#chatInput');
        input.value = ${JSON.stringify(message)};
        document.querySelector('#chatForm').requestSubmit();
      })()`);
      await cdp.waitFor(
        `document.querySelector('#chatStatus')?.textContent === ${JSON.stringify(expectedStatus)} && document.querySelector('#chatForm')?.getAttribute('aria-busy') === "false"`,
        10_000,
        `chat completion for ${message}`
      );
    }

    await submit("First question", "Atbilde pabeigta.");
    assert.deepEqual(state.chatRequests[0], {
      message: "First question",
      history: []
    });

    await submit("Second question", "Atbilde pabeigta.");
    assert.deepEqual(state.chatRequests[1], {
      message: "Second question",
      history: [
        { role: "user", content: "First question" },
        { role: "assistant", content: "Browser reply" }
      ]
    });

    await submit("Trigger failure", "Synthetic chat failure");
    await submit("After failure", "Atbilde pabeigta.");
    assert.equal(state.chatRequests.length, 4);
    assert.deepEqual(state.chatRequests[3], {
      message: "After failure",
      history: [
        { role: "user", content: "First question" },
        { role: "assistant", content: "Browser reply" },
        { role: "user", content: "Second question" },
        { role: "assistant", content: "Browser reply" }
      ]
    });
    assert.equal(
      state.chatRequests[3].history.some((row) => row.content === "Trigger failure"),
      false
    );

    state.statsMode = "stale";
    await cdp.navigate(`${baseUrl}/`);
    await cdp.waitFor(
      `document.querySelector('#liveDot')?.dataset.state === "stale"`,
      10_000,
      "stale statistics rendering"
    );

    state.statsMode = "invalid";
    await cdp.navigate(`${baseUrl}/`);
    await cdp.waitFor(
      `document.querySelector('#liveDot')?.dataset.state === "offline" && document.querySelector('#statsUpdated')?.textContent === "—"`,
      10_000,
      "invalid statistics rejection"
    );

    const links = await cdp.evaluate(`(() => [...document.querySelectorAll('a[href]')].map((node) => node.getAttribute('href')))()`);
    assert(links.includes("/cv-lv.pdf"));
    assert(links.includes("/smarthome.html"));
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

const state = { statsMode: "live", chatRequests: [] };
const server = createFixtureServer(state);
try {
  const address = await listen(server);
  await runBrowserSmoke(`http://127.0.0.1:${address.port}`, state);
  console.log("BROWSER_BEHAVIOR_SMOKE=PASS");
} finally {
  await closeServer(server);
}