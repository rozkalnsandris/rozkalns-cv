#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

const ROOT = resolve(import.meta.dirname, '..');
const LANGUAGES = ['en', 'de', 'lv'];
const OUTPUTS = { en: 'html/cv.pdf', de: 'html/cv-de.pdf', lv: 'html/cv-lv.pdf' };
const TITLES = {
  en: 'Andris Rožkalns — CV',
  de: 'Andris Rožkalns — Lebenslauf',
  lv: 'Andris Rožkalns — CV'
};
const LOCATIONS = {
  en: 'Dortmund, Germany',
  de: 'Dortmund, Deutschland',
  lv: 'Dortmund, Vācija'
};
const AVAILABILITY = {
  en: 'Available from January 2027',
  de: 'Verfügbar ab Januar 2027',
  lv: 'Pieejams no 2027. gada janvāra'
};

// Recruiter-first order: infrastructure -> observability -> differentiator.
const SELECTED_PROJECTS = ['p1', 'p3', 'p2'];

// Keep the full chronology while reducing non-IT visual dominance.
const EXPERIENCE_BULLETS = {
  e1: ['b1'],
  e2: ['b1'],
  e3: ['b1'],
  e4: ['b1']
};

const LEVELS = {
  en: { Latvian: 'Native', English: 'Fluent', German: 'B1' },
  de: { Latvian: 'Muttersprache', English: 'Fließend', German: 'B1' },
  lv: { Latvian: 'Dzimtā', English: 'Brīvi', German: 'B1' }
};

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function required(value, label) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`missing ${label}`);
  }
  return value.trim();
}

function section(title, body) {
  return `<section class="section"><h2>${escapeHtml(title)}</h2>${body}</section>`;
}

function renderHtml(language, profile, messages) {
  const identity = profile.identity;
  const contact = profile.contact;

  if (contact.phone?.visibility !== 'runtime-protected') {
    throw new Error('protected phone contract changed');
  }

  const publicEmail = required(contact.email?.value, 'public email');
  const publicGithub = required(contact.github?.value, 'public GitHub');
  const publicWebsite = required(contact.website?.value, 'public website');

  const experience = [1, 2, 3, 4].map((index) => {
    const prefix = `e${index}`;
    const bullets = EXPERIENCE_BULLETS[prefix].map((suffix) =>
      required(messages[`${prefix}_${suffix}`], `${prefix}_${suffix}`)
    );

    return `<article class="job">
      <div class="job-head">
        <div class="job-title">${escapeHtml(required(messages[`${prefix}_title`], `${prefix}_title`))}
          <span class="org">· ${escapeHtml(required(messages[`${prefix}_org`], `${prefix}_org`))}</span>
        </div>
        <div class="date">${escapeHtml(required(messages[`${prefix}_dates`], `${prefix}_dates`))}</div>
      </div>
      <ul>${bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    </article>`;
  }).join('');

  const projects = SELECTED_PROJECTS.map((prefix) => `<article class="project">
    <div class="project-title">${escapeHtml(required(messages[`${prefix}_title`], `${prefix}_title`))}</div>
    <div class="project-desc">${escapeHtml(required(messages[`pdf_${prefix}_desc`], `pdf_${prefix}_desc`))}</div>
  </article>`).join('');

  const skillItemKeys = {
    core: 'skills_core_items',
    working: 'pdf_skills_working_items',
    learning: 'skills_learning_items',
    foundations: 'pdf_skills_foundations_items'
  };

  const skills = ['core', 'working', 'learning', 'foundations'].map((key) =>
    `<div class="skill-label">${escapeHtml(required(messages[`skills_${key}`], `skills_${key}`))}</div>` +
    `<div class="skill-items">${escapeHtml(required(messages[skillItemKeys[key]], skillItemKeys[key]))}</div>`
  ).join('');

  const education = [1, 2, 3].map((index) => `<article class="education-item">
    <div class="education-title">${escapeHtml(required(messages[`ed${index}_title`], `ed${index}_title`))}</div>
    <div class="education-sub">${escapeHtml(required(messages[`ed${index}_sub`], `ed${index}_sub`))}
      · ${escapeHtml(required(messages[`ed${index}_dates`], `ed${index}_dates`))}</div>
  </article>`).join('');

  const languageRows = profile.languages.map((entry) => {
    const key = entry.name.toLowerCase();
    const label = required(messages[`profile_lang_${key}`], `profile_lang_${key}`);
    const level = LEVELS[language]?.[entry.name];
    if (!level) {
      throw new Error(`missing localized language level for ${language}:${entry.name}`);
    }
    return `<div class="language-row"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(level)}</span></div>`;
  }).join('');

  return `<!doctype html>
<html lang="${language}">
<head>
<meta charset="utf-8">
<title>${escapeHtml(TITLES[language])}</title>
<style>
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }

html,
body {
  margin: 0;
  padding: 0;
  background: #fff;
}

body {
  font-family: Arial, Helvetica, sans-serif;
  color: #282d34;
  font-size: 9.75pt;
  line-height: 1.28;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

.page {
  width: 210mm;
  height: 297mm;
  overflow: hidden;
  padding: 11mm 13mm 9mm;
}

header {
  border-bottom: 1.5px solid #c87922;
  padding-bottom: 5.5mm;
}

h1 {
  margin: 0 0 1.5mm;
  color: #20242a;
  font-size: 24pt;
  line-height: 1;
}

.role {
  margin-bottom: 2.1mm;
  color: #bd701e;
  font-size: 11.8pt;
  font-weight: 700;
}

.contact {
  display: flex;
  flex-wrap: wrap;
  gap: 1.4mm 3.5mm;
  color: #66707b;
  font-size: 8.45pt;
}

.contact a {
  color: #414a54;
  text-decoration: none;
}

.section {
  margin-top: 5.5mm;
}

h2 {
  margin: 0 0 2.8mm;
  padding-bottom: .85mm;
  border-bottom: 1px solid #d8dde3;
  color: #bd701e;
  font-size: 9.75pt;
  line-height: 1.1;
  letter-spacing: .085em;
  text-transform: uppercase;
}

.profile {
  font-size: 9.75pt;
}

.profile p {
  margin: 0;
}

.skills {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 1.4mm 3mm;
  align-items: start;
}

.skill-label {
  font-size: 9pt;
  font-weight: 700;
}

.skill-items {
  font-size: 9pt;
}

.projects {
  display: grid;
  gap: 3.0mm;
}

.project {
  break-inside: avoid;
}

.project-title {
  font-size: 9.2pt;
  font-weight: 700;
}

.project-desc {
  margin-top: .25mm;
  color: #3d444c;
  font-size: 9.2pt;
}

.job {
  margin: 0 0 2.8mm;
  break-inside: avoid;
}

.job-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4mm;
  align-items: baseline;
}

.job-title {
  font-size: 9.2pt;
  font-weight: 700;
}

.org {
  color: #bd701e;
}

.date {
  color: #707983;
  font-size: 8pt;
  white-space: nowrap;
}

ul {
  margin: .5mm 0 0 4.4mm;
  padding: 0;
}

li {
  margin: 0 0 .35mm;
  padding-left: .55mm;
  font-size: 9pt;
}

li::marker {
  color: #d8a764;
}

.education-item {
  margin-bottom: 2.4mm;
  break-inside: avoid;
}

.education-title {
  font-size: 9.1pt;
  font-weight: 700;
}

.education-sub {
  margin-top: .2mm;
  color: #6d7580;
  font-size: 8.5pt;
}

.languages {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5mm 7mm;
}

.language-row {
  display: flex;
  gap: 1.4mm;
  font-size: 9pt;
}

.language-row strong {
  color: #343b43;
}
</style>
</head>
<body>
<main class="page">
<header>
  <h1>${escapeHtml(identity.name)}</h1>
  <div class="role">${escapeHtml(required(messages.role, 'role'))}</div>
  <div class="contact">
    <span>${escapeHtml(LOCATIONS[language])}</span>
    <span>${escapeHtml(AVAILABILITY[language])}</span>
    <a href="mailto:${escapeHtml(publicEmail)}">${escapeHtml(publicEmail)}</a>
    <a href="${escapeHtml(publicGithub)}">github.com/rozkalnsandris</a>
    <a href="${escapeHtml(publicWebsite)}">rozkalns.net</a>
  </div>
</header>

${section(
  required(messages.pdf_profile_title, 'pdf_profile_title'),
  `<div class="profile"><p>${escapeHtml(required(messages.pdf_profile_summary, 'pdf_profile_summary'))}</p></div>`
)}

${section(messages.skills_title, `<div class="skills">${skills}</div>`)}

${section(required(messages.pdf_projects_title, 'pdf_projects_title'), `<div class="projects">${projects}</div>`)}

${section(messages.experience_title, experience)}

${section(messages.education_title, education)}

${section(
  messages.profile_languages_label,
  `<div class="languages">${languageRows}</div>`
)}
</main>
</body>
</html>`;
}

async function findChrome() {
  const candidates = [process.env.CHROME_BIN, 'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'].filter(Boolean);
  for (const candidate of candidates) {
    const child = spawn(candidate, ['--version'], { stdio: 'ignore' });
    const code = await new Promise((resolve) => child.once('exit', resolve));
    if (code === 0) return candidate;
  }
  throw new Error('Chromium/Chrome not found; set CHROME_BIN');
}

async function readPort(profile) {
  const file = join(profile, 'DevToolsActivePort');
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    try {
      const [line] = (await readFile(file, 'utf8')).trim().split(/\r?\n/);
      if (/^[0-9]+$/.test(line)) return Number(line);
    } catch {}
    await delay(100);
  }
  throw new Error('Chrome did not publish DevToolsActivePort');
}

async function fetchJson(url, options = {}) {
  const deadline = Date.now() + 20_000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return await response.json();
      lastError = new Error(`${response.status} ${response.statusText}`);
    } catch (error) { lastError = error; }
    await delay(100);
  }
  throw lastError || new Error(`timed out fetching ${url}`);
}

class Cdp {
  constructor(url) { this.socket = new WebSocket(url); this.id = 1; this.pending = new Map(); this.events = new Map(); }
  async open() {
    await new Promise((resolve, reject) => {
      this.socket.addEventListener('open', resolve, { once: true });
      this.socket.addEventListener('error', () => reject(new Error('CDP open failed')), { once: true });
    });
    this.socket.addEventListener('message', (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        message.error ? pending.reject(new Error(message.error.message)) : pending.resolve(message.result || {});
        return;
      }
      for (const callback of this.events.get(message.method) || []) callback(message.params || {});
    });
  }
  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
  wait(method, timeout = 15_000) {
    return new Promise((resolve, reject) => {
      const callbacks = this.events.get(method) || new Set();
      const done = (params) => { clearTimeout(timer); callbacks.delete(done); resolve(params); };
      const timer = setTimeout(() => { callbacks.delete(done); reject(new Error(`timeout waiting for ${method}`)); }, timeout);
      callbacks.add(done); this.events.set(method, callbacks);
    });
  }
  close() { this.socket.close(); }
}

function assertPdfStructure(bytes, language) {
  const text = bytes.toString('latin1');
  const pageCount = (text.match(/\/Type\s*\/Page\b/g) || []).length;
  if (pageCount !== 1) throw new Error(`${language} PDF must be exactly one page, got ${pageCount}`);
  if (!text.includes('/StructTreeRoot')) throw new Error(`${language} PDF is missing tagged structure`);
  if (!text.includes('/Lang')) throw new Error(`${language} PDF is missing document language metadata`);
}

async function main() {
  const profile = JSON.parse(await readFile(join(ROOT, 'content/profile.json'), 'utf8'));
  const translations = Object.fromEntries(await Promise.all(LANGUAGES.map(async (language) => [language, JSON.parse(await readFile(join(ROOT, `content/translations/${language}.json`), 'utf8'))])));
  const chromeBin = await findChrome();
  const profileDir = await mkdtemp(join(tmpdir(), 'rozkalns-cv-pdf-'));
  const chrome = spawn(chromeBin, [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-background-networking',
    '--disable-component-update', '--disable-default-apps', '--disable-sync', '--metrics-recording-only', '--no-first-run',
    '--remote-debugging-port=0', `--user-data-dir=${profileDir}`, 'about:blank'
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  let stderr = '';
  chrome.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
  let cdp;
  try {
    const port = await readPort(profileDir);
    const target = await fetchJson(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' });
    cdp = new Cdp(target.webSocketDebuggerUrl);
    await cdp.open();
    await cdp.send('Page.enable');
    for (const language of LANGUAGES) {
      const html = renderHtml(language, profile, translations[language]);
      const loaded = cdp.wait('Page.loadEventFired');
      await cdp.send('Page.navigate', { url: `data:text/html;base64,${Buffer.from(html).toString('base64')}` });
      await loaded;
      const fit = await cdp.send('Runtime.evaluate', {
        expression: `(() => {
          const page = document.querySelector('.page');
          if (!page) return { ok: false, reason: 'missing-page' };
          return {
            ok: page.scrollHeight <= page.clientHeight + 1 && page.scrollWidth <= page.clientWidth + 1,
            scrollHeight: page.scrollHeight,
            clientHeight: page.clientHeight,
            scrollWidth: page.scrollWidth,
            clientWidth: page.clientWidth
          };
        })()`,
        returnByValue: true
      });
      if (!fit.result?.value?.ok) throw new Error(`${language} A4 layout overflow: ${JSON.stringify(fit.result?.value)}`);
      const result = await cdp.send('Page.printToPDF', {
        displayHeaderFooter: false,
        printBackground: true,
        preferCSSPageSize: true,
        generateTaggedPDF: true,
        generateDocumentOutline: true
      });
      if (!result.data) throw new Error(`no PDF data for ${language}`);
      const bytes = Buffer.from(result.data, 'base64');
      assertPdfStructure(bytes, language);
      await writeFile(join(ROOT, OUTPUTS[language]), bytes);
      console.log(`PDF_GENERATED=${language}:${OUTPUTS[language]}:${bytes.length}`);
    }
  } finally {
    try { cdp?.close(); } catch {}
    if (chrome.exitCode === null) chrome.kill('SIGTERM');
    await delay(250);
    if (chrome.exitCode === null) chrome.kill('SIGKILL');
    await rm(profileDir, { recursive: true, force: true });
  }
  if (chrome.exitCode && chrome.exitCode !== 0) throw new Error(stderr || `Chrome exited ${chrome.exitCode}`);
  console.log('PDF_GENERATION=PASS');
}

await main();
