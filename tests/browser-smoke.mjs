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
  [".jpeg", "image/jpeg"],
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
  const routed = pathname.endsWith("/") ? `${pathname}index.html` : pathname;
  const decoded = decodeURIComponent(routed);
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

      if (url.pathname === "/api/contact-config" && request.method === "GET") {
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(JSON.stringify({ configured: true, sitekey: "fixture-site-key" }));
        return;
      }

      if (url.pathname === "/api/contact-reveal" && request.method === "POST") {
        const body = JSON.parse(await readRequestBody(request));
        state.contactRequests.push(body);
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(JSON.stringify({
          email: "test@example.invalid",
          phone: "+49 123 4567890",
          phone_uri: "+491234567890"
        }));
        return;
      }

      if (url.pathname === "/api/chat-config" && request.method === "GET") {
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(JSON.stringify({ configured: true, sitekey: "fixture-chat-site-key" }));
        return;
      }

      if (url.pathname === "/api/chat-admission" && request.method === "POST") {
        const body = JSON.parse(await readRequestBody(request));
        state.chatAdmissionRequests.push(body);
        response.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store"
        });
        response.end(JSON.stringify({ session: "fixture-chat-session" }));
        return;
      }

      if (url.pathname === "/api/chat" && request.method === "POST") {
        const admission = request.headers["x-chat-admission"];
        state.chatAdmissionHeaders.push(admission);
        if (admission !== "fixture-chat-session") {
          response.writeHead(401, {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store"
          });
          response.end(JSON.stringify({ reply: "Missing chat admission" }));
          return;
        }
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

      if (url.pathname.startsWith("/i18n/") && state.translationDelayMs > 0) {
        const translationDelayMs = state.translationDelayMs;
        state.translationDelayMs = 0;
        await delay(translationDelayMs);
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
    const virtualKeyCode = key === "Escape" ? 27 : key === "Tab" ? 9 : key === "Enter" ? 13 : 0;
    const keyParams = {
      key,
      code: key,
      modifiers,
      ...(virtualKeyCode ? {
        windowsVirtualKeyCode: virtualKeyCode,
        nativeVirtualKeyCode: virtualKeyCode
      } : {})
    };
    await this.send("Input.dispatchKeyEvent", {
      type: key === "Enter" ? "keyDown" : "rawKeyDown",
      ...(key === "Enter" ? { text: "\r", unmodifiedText: "\r" } : {}),
      ...keyParams
    });
    await this.send("Input.dispatchKeyEvent", {
      type: "keyUp",
      ...keyParams
    });
  }

  close() {
    this.socket.close();
  }
}

async function runBrowserSmoke(baseUrl, state) {
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

    await cdp.navigate(`${baseUrl}/en/`);
    const firstRenderSkillIcons = await cdp.evaluate(`(() => ({
      chips: document.querySelectorAll(".skill-chip").length,
      icons: document.querySelectorAll(".skill-chip svg").length
    }))()`);
    assert.ok(firstRenderSkillIcons.chips > 0);
    assert.equal(firstRenderSkillIcons.icons, firstRenderSkillIcons.chips);

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

    const skillIconContract = await cdp.evaluate(`(() => [...document.querySelectorAll(".skill-chip")].map((chip) => {
      const svg = chip.querySelector("svg");
      const box = svg?.getBBox();
      return {
        label: chip.textContent.trim(),
        iconCount: chip.querySelectorAll("svg").length,
        box: box ? { x: box.x, y: box.y, width: box.width, height: box.height } : null
      };
    }))()`);
    assert.ok(skillIconContract.length > 0);
    for (const icon of skillIconContract) {
      assert.equal(icon.iconCount, 1, icon.label);
      assert.ok(icon.box, icon.label);
      assert.ok(icon.box.x >= 0 && icon.box.y >= 0, icon.label);
      assert.ok(icon.box.x + icon.box.width <= 24, icon.label);
      assert.ok(icon.box.y + icon.box.height <= 24, icon.label);
    }
    const shieldIcon = skillIconContract.find((icon) => icon.label === "SSL/TLS");
    const codeIcon = skillIconContract.find((icon) => icon.label === "Python");
    assert.ok(shieldIcon?.box.width >= 12);
    assert.ok(codeIcon?.box.width >= 12);

    const initialContract = await cdp.evaluate(`(() => ({
      title: document.title,
      role: document.querySelector('[data-i18n="role"]')?.textContent,
      pdf: document.querySelector('#pdfLink')?.getAttribute('href'),
      dialogModal: document.querySelector('#chatDialog')?.getAttribute('aria-modal'),
      privacy: document.querySelector('[data-i18n="chat_privacy"]')?.textContent,
      photoSrc: document.querySelector('.profile-photo')?.currentSrc,
      photoAlt: document.querySelector('.profile-photo')?.getAttribute('alt'),
      profileHeading: document.querySelector('.hero-shell h1')?.textContent,
      location: document.querySelector('#profileLocation')?.textContent,
      photoNaturalWidth: document.querySelector('.profile-photo')?.naturalWidth,
      photoNaturalHeight: document.querySelector('.profile-photo')?.naturalHeight
    }))()`);
    assert.equal(initialContract.title, "Andris Rožkalns · DevOps & Linux Engineer");
    assert.equal(initialContract.role, "Junior DevOps & Linux Engineer");
    assert.match(initialContract.photoSrc, /\/assets\/photo\.[0-9a-f]{12}\.webp$/);
    assert.equal(initialContract.photoAlt, "");
    assert.equal(initialContract.profileHeading, "Andris Rožkalns");
    assert.equal(initialContract.location, "Dortmund, Germany");
    assert.equal(initialContract.photoNaturalWidth, 480);
    assert.equal(initialContract.photoNaturalHeight, 480);
    assert.equal(initialContract.pdf, "/cv.pdf");
    assert.equal(initialContract.dialogModal, "true");
    assert.match(initialContract.privacy, /raw IP addresses are not stored/i);
    const initialLanguageState = await cdp.evaluate(`(() => ({
      groupRole: document.querySelector('.language-switcher')?.getAttribute('role'),
      groupLabel: document.querySelector('.language-switcher')?.getAttribute('aria-label'),
      controls: [...document.querySelectorAll('.language-switcher [data-lang]')].map((control) => ({
        language: control.dataset.lang,
        label: control.getAttribute('aria-label'),
        href: control.getAttribute('href'),
        current: control.getAttribute('aria-current')
      })),
      logLive: document.querySelector('#chatLog')?.getAttribute('aria-live'),
      statusRole: document.querySelector('#chatStatus')?.getAttribute('role'),
      profileListRole: document.querySelector('.profile-languages')?.getAttribute('role'),
      profileListLabel: document.querySelector('.profile-languages')?.getAttribute('aria-label'),
      profileListItems: [...document.querySelectorAll('.profile-languages .profile-language')].map((item) => item.getAttribute('role'))
    }))()`);
    assert.equal(initialLanguageState.groupRole, "group");
    assert.equal(initialLanguageState.groupLabel, "Languages");
    assert.deepEqual(initialLanguageState.controls, [
      { language: "en", label: "English", href: "/en/", current: "page" },
      { language: "de", label: "Deutsch", href: "/de/", current: null },
      { language: "lv", label: "Latviešu", href: "/lv/", current: null }
    ]);
    assert.equal(initialLanguageState.logLive, "polite");
    assert.equal(initialLanguageState.statusRole, "status");
    assert.equal(initialLanguageState.profileListRole, "list");
    assert.equal(initialLanguageState.profileListLabel, "Languages");
    assert.deepEqual(initialLanguageState.profileListItems, ["listitem", "listitem", "listitem"]);

    const germanLoaded = cdp.waitForEvent("Page.loadEventFired", 15_000);
    await cdp.evaluate(`document.querySelector('[data-lang="de"]').click()`);
    await germanLoaded;
    await cdp.waitFor(
      `location.pathname === "/de/" && document.documentElement.lang === "de" && document.querySelector('#profileLocation')?.textContent === "Dortmund, Deutschland"`,
      10_000,
      "German localized URL"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#profileLocation')?.textContent`),
      "Dortmund, Deutschland"
    );

    const latvianLoaded = cdp.waitForEvent("Page.loadEventFired", 15_000);
    await cdp.evaluate(`document.querySelector('[data-lang="lv"]').click()`);
    await latvianLoaded;
    await cdp.waitFor(
      `location.pathname === "/lv/" && document.documentElement.lang === "lv" && document.title === "Andris Rožkalns · DevOps un Linux inženieris" && document.querySelector('#pdfLink')?.getAttribute('href') === "/cv-lv.pdf"`,
      10_000,
      "Latvian localized URL"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('[data-i18n="role"]').textContent`),
      "Junior DevOps un Linux inženieris"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#profileLocation')?.textContent`),
      "Dortmund, Vācija"
    );
    assert.deepEqual(
      await cdp.evaluate(`[...document.querySelectorAll('.language-switcher [data-lang]')].map((control) => [control.dataset.lang, control.getAttribute('aria-current')])`),
      [["en", null], ["de", null], ["lv", "page"]]
    );
    assert.deepEqual(
    await cdp.evaluate(`(() => ({
      language: document.querySelector('.language-switcher')?.getAttribute('aria-label'),
      focus: document.querySelector('.focus-tags')?.getAttribute('aria-label'),
      navigation: document.querySelector('.site-nav')?.getAttribute('aria-label'),
      profileListRole: document.querySelector('.profile-languages')?.getAttribute('role'),
      profileListLabel: document.querySelector('.profile-languages')?.getAttribute('aria-label'),
      profileListItems: [...document.querySelectorAll('.profile-languages .profile-language')].map((item) => item.getAttribute('role'))
    }))()`),
    {
      language: "Valodas",
      focus: null,
      navigation: "CV",
      profileListRole: "list",
      profileListLabel: "Valodas",
      profileListItems: ["listitem", "listitem", "listitem"]
    }
  );

    await cdp.evaluate(`(() => {
      const launcher = document.querySelector('#chatLauncher');
      launcher.focus();
      launcher.click();
    })()`);
    await cdp.waitFor(
      `document.querySelector('#chatBackdrop').hidden === false && document.activeElement?.id === "chatInput" && document.querySelector('#pageShell').inert === true`,
      5_000,
      "accessible dialog focus"
    );
    await cdp.evaluate(`document.querySelector('#chatClose').focus()`);
    await cdp.key("Tab", 8);
    assert.equal(await cdp.evaluate(`document.activeElement?.id`), "chatSend");
    await cdp.key("Tab");
    assert.equal(await cdp.evaluate(`document.activeElement?.id`), "chatClose");
    await cdp.key("Escape");
    await cdp.waitFor(
      `document.querySelector('#chatBackdrop').hidden === true && document.activeElement?.id === "chatLauncher" && document.querySelector('#pageShell').inert === false`,
      5_000,
      "Escape dialog dismissal"
    );

    await cdp.evaluate(`(() => {
      const launcher = document.querySelector('#chatLauncher');
      launcher.focus();
      launcher.click();
    })()`);
    await cdp.waitFor(`document.activeElement?.id === "chatInput"`, 5_000, "chat input focus");
    await cdp.evaluate(`(() => {
      window.turnstile = {
        render(mount, options) {
          const frame = document.createElement('iframe');
          frame.title = 'Synthetic Chat Turnstile';
          frame.tabIndex = 0;
          mount.append(frame);
          setTimeout(() => options.callback('synthetic-chat-turnstile-token'), 0);
          return 'fixture-chat-widget';
        },
        reset() {}
      };
    })()`);

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
    const announcementContract = await cdp.evaluate(`(() => ({
      answerLive: document.querySelector('#chatLog .message.bot:last-child')?.getAttribute('aria-live'),
      logLive: document.querySelector('#chatLog')?.getAttribute('aria-live'),
      statusRole: document.querySelector('#chatStatus')?.getAttribute('role'),
      statusLive: document.querySelector('#chatStatus')?.getAttribute('aria-live')
    }))()`);
    assert.equal(announcementContract.answerLive, "off");
    assert.equal(announcementContract.logLive, "polite");
    assert.equal(announcementContract.statusRole, "status");
    assert.equal(announcementContract.statusLive, "polite");
    assert.deepEqual(state.chatAdmissionRequests, [{ token: "synthetic-chat-turnstile-token" }]);
    assert.deepEqual(state.chatAdmissionHeaders, ["fixture-chat-session"]);
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

    await submit(
      "Trigger failure",
      "Savienojuma kļūda — lūdzu, rakstiet Andrim e-pastā."
    );
    const failureBubble = await cdp.evaluate(
      `document.querySelector('#chatLog .message.bot:last-child')?.textContent`
    );
    assert.equal(failureBubble, "Synthetic chat failure");

    await submit("After failure", "Atbilde pabeigta.");
    assert.equal(state.chatRequests.length, 4);
    assert.deepEqual(state.chatAdmissionRequests, [{ token: "synthetic-chat-turnstile-token" }]);
    assert.deepEqual(state.chatAdmissionHeaders, [
      "fixture-chat-session",
      "fixture-chat-session",
      "fixture-chat-session",
      "fixture-chat-session"
    ]);
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

    await cdp.key("Escape");
    await cdp.waitFor(
      `document.querySelector('#chatBackdrop').hidden === true && document.activeElement?.id === "chatLauncher"`,
      5_000,
      "chat focus return before contact verification"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#contactEmail')?.getAttribute('href')`),
      "mailto:andris@rozkalns.net"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('#contactPhone')?.tagName`),
      "SPAN"
    );
    await cdp.evaluate(`(() => {
      window.turnstile = {
        render(mount, options) {
          const frame = document.createElement('iframe');
          frame.title = 'Synthetic Turnstile';
          frame.tabIndex = 0;
          mount.append(frame);
          setTimeout(() => options.callback('synthetic-turnstile-token'), 0);
          return 'fixture-widget';
        },
        reset() {}
      };
      document.querySelector('#contactReveal').focus();
    })()`);
    await cdp.key("Enter");
    await cdp.waitFor(
      `document.querySelector('#contactReveal')?.hidden === true && document.querySelector('#turnstileMount')?.hidden === true && document.querySelector('#contactVerifyStatus')?.dataset.state === "success" && document.activeElement?.dataset.revealed === "true"`,
      10_000,
      "keyboard WhatsApp phone verification focus transfer"
    );
    assert.deepEqual(state.contactRequests, [{ token: "synthetic-turnstile-token" }]);
    assert.equal(
      await cdp.evaluate(`document.activeElement?.getAttribute('href')`),
      "https://wa.me/491234567890"
    );
    assert.equal(
      await cdp.evaluate(`document.querySelector('.contacts a[href^="https://wa.me/"]')?.getAttribute('href')`),
      "https://wa.me/491234567890"
    );

    state.statsMode = "stale";
    await cdp.navigate(`${baseUrl}/lv/`);
    await cdp.waitFor(
      `document.querySelector('#liveDot')?.dataset.state === "stale"`,
      10_000,
      "stale statistics rendering"
    );

    state.statsMode = "invalid";
    await cdp.navigate(`${baseUrl}/lv/`);
    await cdp.waitFor(
      `document.querySelector('#liveDot')?.dataset.state === "offline" && document.querySelector('#statsUpdated')?.textContent === "—"`,
      10_000,
      "invalid statistics rejection"
    );

    const readLinkState = () => cdp.evaluate(`(() => ({
      readyState: document.readyState,
      language: document.documentElement.lang,
      pdfHref: document.querySelector('#pdfLink')?.getAttribute('href') ?? null,
      hrefs: [...document.querySelectorAll('a[href]')].map((node) => node.getAttribute('href'))
    }))()`);
    try {
      await cdp.waitFor(
        `document.readyState === "complete" && document.documentElement.lang === "lv" && document.querySelector('#pdfLink')?.getAttribute('href') === "/cv-lv.pdf"`,
        10_000,
        "restored Latvian link state after navigation"
      );
    } catch (error) {
      const diagnostics = await readLinkState();
      throw new Error(`${error instanceof Error ? error.message : error}; link-state=${JSON.stringify(diagnostics)}`);
    }

    const linkState = await readLinkState();
    assert.equal(linkState.language, "lv", `link-state=${JSON.stringify(linkState)}`);
    assert.equal(linkState.pdfHref, "/cv-lv.pdf", `link-state=${JSON.stringify(linkState)}`);
    assert(linkState.hrefs.includes("/cv-lv.pdf"), `link-state=${JSON.stringify(linkState)}`);
    assert(linkState.hrefs.includes("/smarthome.html"), `link-state=${JSON.stringify(linkState)}`);

    const responsiveMatrix = [
      { width: 390, height: 844, mobile: true },
      { width: 430, height: 932, mobile: true },
      { width: 768, height: 1024, mobile: false },
      { width: 1280, height: 900, mobile: false },
      { width: 1440, height: 1000, mobile: false }
    ];
    const localeMatrix = [
      { path: "/en/", language: "en", location: "Dortmund, Germany", label: "English" },
      { path: "/de/", language: "de", location: "Dortmund, Deutschland", label: "German" },
      { path: "/lv/", language: "lv", location: "Dortmund, Vācija", label: "Latvian" }
    ];
    for (const locale of localeMatrix) {
      for (const viewport of responsiveMatrix) {
        await cdp.send("Emulation.setDeviceMetricsOverride", {
          ...viewport,
          deviceScaleFactor: 1
        });
        await cdp.navigate(`${baseUrl}${locale.path}`);
        await cdp.waitFor(
          `document.documentElement.lang === ${JSON.stringify(locale.language)} && document.querySelector('#profileLocation')?.textContent === ${JSON.stringify(locale.location)}`,
          10_000,
          `responsive ${viewport.width}px ${locale.label} restoration`
        );
        const layout = await cdp.evaluate(`(() => {
          const page = document.querySelector('#pageShell')?.getBoundingClientRect();
          const locationRow = document.querySelector('#profileLocation')?.closest('.contact-row');
          const primaryTargets = [...document.querySelectorAll(
            '.language-switcher [data-lang], .actions .button, #contactReveal, #chatLauncher'
          )].filter((element) => {
            const rect = element.getBoundingClientRect();
            return !element.hidden && rect.width > 0 && rect.height > 0;
          }).map((element) => {
            const rect = element.getBoundingClientRect();
            return {
              id: element.id || element.textContent.trim(),
              width: rect.width,
              height: rect.height
            };
          });
          return {
            innerWidth: window.innerWidth,
            documentClientWidth: document.documentElement.clientWidth,
            documentScrollWidth: document.documentElement.scrollWidth,
            bodyScrollWidth: document.body.scrollWidth,
            page: page ? { left: page.left, right: page.right, width: page.width } : null,
            location: locationRow ? {
              clientWidth: locationRow.clientWidth,
              scrollWidth: locationRow.scrollWidth
            } : null,
            primaryTargets
          };
        })()`);
        const context = `${locale.label} ${viewport.width}px`;
        assert.equal(layout.innerWidth, viewport.width, `${context} viewport width`);
        assert.ok(
          layout.documentScrollWidth <= layout.documentClientWidth,
          `${context} document overflow: ${JSON.stringify(layout)}`
        );
        assert.ok(
          layout.bodyScrollWidth <= layout.documentClientWidth,
          `${context} body overflow: ${JSON.stringify(layout)}`
        );
        assert.ok(layout.page, `${context} page shell missing`);
        assert.ok(layout.page.left >= -0.5, `${context} page left overflow`);
        assert.ok(layout.page.right <= viewport.width + 0.5, `${context} page right overflow`);
        assert.ok(layout.location, `${context} location row missing`);
        assert.ok(
          layout.location.scrollWidth <= layout.location.clientWidth,
          `${context} location overflow: ${JSON.stringify(layout.location)}`
        );
        assert.ok(layout.primaryTargets.length >= 7, `${context} primary targets missing`);
        for (const target of layout.primaryTargets) {
          assert.ok(target.height >= 48, `${context} target below 48px: ${JSON.stringify(target)}`);
        }
      }
    }

    await cdp.send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: "reduce" }]
    });
    await cdp.navigate(`${baseUrl}/en/`);
    await cdp.waitFor(
      `document.readyState === "complete" && document.documentElement.lang === "en"`,
      10_000,
      "reduced-motion English restoration"
    );
    const reducedMotion = await cdp.evaluate(`(() => ({
      scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
      transitionDurations: getComputedStyle(document.querySelector('.button')).transitionDuration
        .split(',')
        .map((value) => Number.parseFloat(value) || 0)
    }))()`);
    assert.equal(reducedMotion.scrollBehavior, "auto");
    assert.ok(reducedMotion.transitionDurations.every((value) => value <= 0.001));
    await cdp.send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: "no-preference" }]
    });

    await cdp.navigate(`${baseUrl}/en/`);
    await cdp.waitFor(
      `document.readyState === "complete" && document.documentElement.lang === "en"`,
      10_000,
      "keyboard-order English restoration"
    );
    await cdp.evaluate(`document.activeElement?.blur()`);
    await cdp.key("Tab");
    assert.equal(await cdp.evaluate(`document.activeElement?.matches('.skip-link')`), true);
    const expectedFocusHrefs = [
      "#about", "#projects", "#skills", "#experience", "#stats", "#education", "/en/"
    ];
    for (const expectedHref of expectedFocusHrefs) {
      await cdp.key("Tab");
      assert.equal(
        await cdp.evaluate(`document.activeElement?.getAttribute('href')`),
        expectedHref,
        `top-level keyboard order before ${expectedHref}`
      );
    }

    await cdp.navigate(`${baseUrl}/smarthome.html`);
    await cdp.waitFor(
      `document.readyState === "complete" && document.documentElement.lang === "lv" && document.querySelector('#demoMain h1')`,
      10_000,
      "Smart Home Latvian initialization"
    );
    const smartSemantics = await cdp.evaluate(`(() => ({
      mainCount: document.querySelectorAll('main').length,
      h1Count: document.querySelectorAll('#demoMain h1').length,
      sectionH2Count: document.querySelectorAll('#demoMain > section > .section-heading > h2').length,
      deviceH3Count: document.querySelectorAll('.demo-device h3').length,
      language: document.documentElement.lang,
      languageRole: document.querySelector('.language-switcher')?.getAttribute('role'),
      groupLabel: document.querySelector('.language-switcher')?.getAttribute('aria-label'),
      languageLabels: [...document.querySelectorAll('.language-switcher [data-lang]')].map((button) => button.getAttribute('aria-label'))
    }))()`);
    assert.equal(smartSemantics.mainCount, 1);
    assert.equal(smartSemantics.h1Count, 1);
    assert.equal(smartSemantics.sectionH2Count, 2);
    assert.equal(smartSemantics.deviceH3Count, 8);
    assert.equal(smartSemantics.language, "lv");
    assert.equal(smartSemantics.languageRole, "group");
    assert.equal(smartSemantics.groupLabel, "Valodas");
    assert.deepEqual(smartSemantics.languageLabels, ["English", "Deutsch", "Latviešu"]);
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
  translationDelayMs: 1200,
  statsMode: "live",
  chatRequests: [],
  chatAdmissionRequests: [],
  chatAdmissionHeaders: [],
  contactRequests: []
};
const server = createFixtureServer(state);
try {
  const address = await listen(server);
  await runBrowserSmoke(`http://127.0.0.1:${address.port}`, state);
  console.log("BROWSER_BEHAVIOR_SMOKE=PASS");
} finally {
  await closeServer(server);
}
