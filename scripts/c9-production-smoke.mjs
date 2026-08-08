import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const TARGET_URL = new URL(process.env.TARGET_URL || "https://rozkalns.net/");
const CHROME_BIN = process.env.CHROME_BIN;
if (!CHROME_BIN) throw new Error("CHROME_BIN is required");
if (TARGET_URL.protocol !== "https:" || TARGET_URL.hostname !== "rozkalns.net") {
  throw new Error("TARGET_URL must be https://rozkalns.net/");
}
if (typeof WebSocket !== "function") throw new Error("Node WebSocket implementation is required");

async function readChromeDebugPort(profile, timeoutMs = 20_000) {
  const file = join(profile, "DevToolsActivePort");
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const [line] = (await readFile(file, "utf8")).trim().split(/\r?\n/);
      if (/^[0-9]+$/.test(line)) return Number(line);
    } catch {}
    await delay(100);
  }
  throw new Error("Chrome did not publish DevToolsActivePort");
}

async function getJson(url, options = {}, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  let error;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return await response.json();
      error = new Error(`${response.status} ${response.statusText}`);
    } catch (candidate) { error = candidate; }
    await delay(100);
  }
  throw error || new Error(`timed out fetching ${url}`);
}

async function stop(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise((resolve) => child.once("exit", resolve));
  child.kill("SIGTERM");
  if (!await Promise.race([exited.then(() => true), delay(3000).then(() => false)])) {
    child.kill("SIGKILL");
    await exited;
  }
}

class Cdp {
  constructor(url) {
    this.socket = new WebSocket(url);
    this.id = 1;
    this.pending = new Map();
    this.listeners = new Map();
  }
  async open() {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP open timeout")), 10_000);
      this.socket.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
      this.socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("CDP connection failed")); }, { once: true });
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
      for (const listener of this.listeners.get(message.method) || []) listener(message.params || {});
    });
  }
  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
  waitForEvent(method, timeoutMs = 15_000) {
    return new Promise((resolve, reject) => {
      const listeners = this.listeners.get(method) || new Set();
      const timer = setTimeout(() => { listeners.delete(onEvent); reject(new Error(`timeout: ${method}`)); }, timeoutMs);
      const onEvent = (params) => { clearTimeout(timer); listeners.delete(onEvent); resolve(params); };
      listeners.add(onEvent);
      this.listeners.set(method, listeners);
    });
  }
  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true, userGesture: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "browser evaluation failed");
    return result.result?.value;
  }
  async waitFor(expression, timeoutMs, label) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (await this.evaluate(expression)) return;
      await delay(75);
    }
    throw new Error(`timeout waiting for ${label}`);
  }
  async navigate(url) {
    const loaded = this.waitForEvent("Page.loadEventFired");
    await this.send("Page.navigate", { url });
    await loaded;
  }
  async key(key, modifiers = 0) {
    const code = key === "Enter" ? 13 : key === "Escape" ? 27 : key === "Tab" ? 9 : 0;
    const params = { key, code: key, modifiers, ...(code ? { windowsVirtualKeyCode: code, nativeVirtualKeyCode: code } : {}) };
    await this.send("Input.dispatchKeyEvent", { type: "rawKeyDown", ...params });
    if (key === "Enter") await this.send("Input.dispatchKeyEvent", { type: "char", text: "\r", unmodifiedText: "\r", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
    await this.send("Input.dispatchKeyEvent", { type: "keyUp", ...params });
  }
  close() { this.socket.close(); }
}

async function runViewport(width, height, label) {
  const profile = await mkdtemp(join(tmpdir(), `rozkalns-c9-${label}-`));
  const child = spawn(CHROME_BIN, [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
    "--disable-background-networking", "--disable-component-update", "--disable-default-apps",
    "--disable-sync", "--no-first-run", "--lang=en-US", "--remote-debugging-port=0",
    `--window-size=${width},${height}`, `--user-data-dir=${profile}`, "about:blank"
  ], { stdio: ["ignore", "ignore", "pipe"] });
  let stderr = "";
  child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
  let cdp;
  try {
    const port = await readChromeDebugPort(profile);
    const target = await getJson(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
    cdp = new Cdp(target.webSocketDebuggerUrl);
    await cdp.open();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Network.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width <= 500 });
    await cdp.send("Network.setBlockedURLs", { urls: ["*://static.cloudflareinsights.com/*", "*://cloudflareinsights.com/*"] });

    await cdp.navigate(TARGET_URL.href);
    await cdp.waitFor(`document.readyState === "complete" && document.documentElement.lang === "en"`, 15_000, `${label} initial document`);
    const challenge = await cdp.evaluate(`document.querySelector('meta[name="robots"][content*="noindex"]') && /Just a moment/i.test(document.title)`);
    assert.equal(Boolean(challenge), false, "Cloudflare challenge replaced production page");
    await cdp.waitFor(`document.querySelector('#liveDot')?.dataset.state === "live"`, 15_000, `${label} live stats`);

    const initial = await cdp.evaluate(`(() => ({
      lang: document.documentElement.lang,
      pdf: document.querySelector('#pdfLink')?.getAttribute('href'),
      stats: document.querySelector('[data-stat="docker_containers"]')?.textContent,
      emailMasked: Boolean(document.querySelector('#contactEmail.contact-masked')),
      phoneMasked: Boolean(document.querySelector('#contactPhone.contact-masked')),
      mailto: Boolean(document.querySelector('.contacts a[href^="mailto:"]')),
      tel: Boolean(document.querySelector('.contacts a[href^="tel:"]')),
      profileDecoded: [document.querySelector('.profile-photo')?.naturalWidth, document.querySelector('.profile-photo')?.naturalHeight],
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
    }))()`);
    assert.equal(initial.lang, "en");
    assert.equal(initial.pdf, "/cv.pdf");
    assert.notEqual(initial.stats, "—");
    assert.equal(initial.emailMasked, true);
    assert.equal(initial.phoneMasked, true);
    assert.equal(initial.mailto, false);
    assert.equal(initial.tel, false);
    assert.deepEqual(initial.profileDecoded, [480, 480]);
    assert.equal(initial.overflow, false);

    for (const [language, pdf] of [["de", "/cv-de.pdf"], ["lv", "/cv-lv.pdf"], ["en", "/cv.pdf"]]) {
      await cdp.evaluate(`document.querySelector('[data-lang="${language}"]').click()`);
      await cdp.waitFor(`document.documentElement.lang === "${language}" && document.querySelector('#pdfLink')?.getAttribute('href') === "${pdf}"`, 10_000, `${label} ${language} language`);
      const state = await cdp.evaluate(`[...document.querySelectorAll('[data-lang]')].map(b => [b.dataset.lang,b.getAttribute('aria-pressed'),b.getAttribute('aria-label')])`);
      assert.equal(state.filter(([, pressed]) => pressed === "true").length, 1);
      assert.equal(state.find(([lang]) => lang === language)?.[1], "true");
      assert.ok(state.every(([, , name]) => typeof name === "string" && name.length > 1));
    }

    // Real production Turnstile is intentionally not solved by automation. Prove only
    // interaction-only loading, keyboard entry, and that protected values remain masked.
    await cdp.evaluate(`document.querySelector('#contactReveal').focus()`);
    await cdp.key("Enter");
    await cdp.waitFor(`document.querySelector('script[src^="https://challenges.cloudflare.com/turnstile/"]') !== null`, 15_000, `${label} Turnstile script`);
    await cdp.waitFor(`document.querySelector('#turnstileMount')?.hidden === false`, 15_000, `${label} Turnstile mount`);
    const protectedState = await cdp.evaluate(`(() => ({
      emailMasked: Boolean(document.querySelector('#contactEmail.contact-masked')),
      phoneMasked: Boolean(document.querySelector('#contactPhone.contact-masked')),
      mailto: Boolean(document.querySelector('.contacts a[href^="mailto:"]')),
      tel: Boolean(document.querySelector('.contacts a[href^="tel:"]')),
      turnstileFrame: Boolean(document.querySelector('#turnstileMount iframe'))
    }))()`);
    assert.equal(protectedState.emailMasked, true);
    assert.equal(protectedState.phoneMasked, true);
    assert.equal(protectedState.mailto, false);
    assert.equal(protectedState.tel, false);
    assert.equal(protectedState.turnstileFrame, true);

    // One bounded production assistant request. Never print prompt or reply text.
    await cdp.evaluate(`document.querySelector('#chatLauncher').focus(); document.querySelector('#chatLauncher').click()`);
    await cdp.waitFor(`document.querySelector('#chatBackdrop')?.hidden === false && document.activeElement?.id === "chatInput"`, 10_000, `${label} chat open`);
    await cdp.evaluate(`(() => { const input = document.querySelector('#chatInput'); input.value = 'C9 automated production health check. Reply briefly with OK.'; document.querySelector('#chatForm').requestSubmit(); })()`);
    await cdp.waitFor(`document.querySelector('#chatForm')?.getAttribute('aria-busy') === "false" && document.querySelector('#chatStatus')?.textContent?.length > 0`, 30_000, `${label} chat completion`);
    const chat = await cdp.evaluate(`(() => ({
      botCount: document.querySelectorAll('#chatLog .message.bot').length,
      statusNonEmpty: Boolean(document.querySelector('#chatStatus')?.textContent?.trim()),
      streamLive: [...document.querySelectorAll('#chatLog .message.bot')].at(-1)?.getAttribute('aria-live')
    }))()`);
    assert.ok(chat.botCount >= 2);
    assert.equal(chat.statusNonEmpty, true);
    assert.equal(chat.streamLive, "off");
    await cdp.key("Escape");
    await cdp.waitFor(`document.querySelector('#chatBackdrop')?.hidden === true && document.activeElement?.id === "chatLauncher"`, 10_000, `${label} chat focus return`);

    await cdp.navigate(new URL("/smarthome.html", TARGET_URL).href);
    await cdp.waitFor(`document.readyState === "complete"`, 10_000, `${label} Smart Home`);
    const smart = await cdp.evaluate(`(() => ({
      h1: document.querySelectorAll('main h1').length,
      h2: document.querySelectorAll('main h2').length,
      h3: document.querySelectorAll('main h3').length,
      main: Boolean(document.querySelector('main#demoMain')),
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
    }))()`);
    assert.deepEqual(smart, { h1: 1, h2: 2, h3: 8, main: true, overflow: false });

    console.log(`C9_BROWSER_${label.toUpperCase()}=PASS`);
  } finally {
    cdp?.close();
    await stop(child);
    await rm(profile, { recursive: true, force: true });
    if (child.exitCode && stderr) process.stderr.write(stderr.slice(-2000));
  }
}

await runViewport(1440, 1000, "desktop");
await runViewport(390, 844, "phone");
console.log("C9_PRODUCTION_BROWSER=PASS");
