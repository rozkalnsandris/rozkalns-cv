import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

export const LOCALIZED_LANGUAGES = Object.freeze(["en", "de", "lv"]);
const ORIGIN = "https://rozkalns.net";
const DEFAULT_URL = `${ORIGIN}/en/`;
const PDFS = Object.freeze({ en: "/cv.pdf", de: "/cv-de.pdf", lv: "/cv-lv.pdf" });
const LOCALES = Object.freeze({ en: "en-GB", de: "de-DE", lv: "lv-LV" });
const SKILL_GROUP_KEYS = Object.freeze([
  "skills_core_items",
  "skills_working_items",
  "skills_learning_items",
  "skills_foundations_items"
]);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function replaceBoundText(html, messages) {
  const keys = [...new Set([...html.matchAll(/\bdata-i18n="([^"]+)"/g)].map((match) => match[1]))];
  for (const key of keys) {
    const value = messages[key];
    if (typeof value !== "string") throw new Error(`missing translation for ${key}`);
    const pattern = new RegExp(
      `(<([a-z][a-z0-9-]*)\\b[^>]*\\bdata-i18n="${escapeRegExp(key)}"[^>]*>)([^<]*)(<\\/\\2>)`,
      "gi"
    );
    let replacements = 0;
    html = html.replace(pattern, (_match, open, _tag, _text, close) => {
      replacements += 1;
      return `${open}${escapeHtml(value)}${close}`;
    });
    if (replacements === 0) throw new Error(`unsupported non-text data-i18n binding: ${key}`);
  }
  return html;
}

function replaceBoundAttribute(html, binding, attribute, messages) {
  const pattern = new RegExp(`<[^>]*\\b${binding}="([^"]+)"[^>]*>`, "gi");
  return html.replace(pattern, (tag, key) => {
    const value = messages[key];
    if (typeof value !== "string") throw new Error(`missing translation for ${binding}:${key}`);
    const attributePattern = new RegExp(`\\b${attribute}="[^"]*"`, "i");
    if (!attributePattern.test(tag)) throw new Error(`missing ${attribute} for ${binding}:${key}`);
    return tag.replace(attributePattern, `${attribute}="${escapeHtml(value)}"`);
  });
}

function replaceSkillChips(html, messages) {
  let groupIndex = 0;
  html = html.replace(/<div class="skill-chips">([\s\S]*?)<\/div>/g, (block, inner) => {
    if (groupIndex >= SKILL_GROUP_KEYS.length) return block;
    const key = SKILL_GROUP_KEYS[groupIndex++];
    const raw = messages[key];
    if (typeof raw !== "string") throw new Error(`missing translation for ${key}`);
    const items = raw.split("·").map((item) => item.trim()).filter(Boolean);
    let itemIndex = 0;
    const localized = inner.replace(
      /(<span class="skill-chip">)([^<]*)(<\/span>)/g,
      (_match, open, _text, close) => {
        const value = items[itemIndex++];
        if (typeof value !== "string") throw new Error(`too few skill items for ${key}`);
        return `${open}${escapeHtml(value)}${close}`;
      }
    );
    if (itemIndex !== items.length) {
      throw new Error(`skill item mismatch for ${key}: html=${itemIndex} translation=${items.length}`);
    }
    return `<div class="skill-chips">${localized}</div>`;
  });
  if (groupIndex !== SKILL_GROUP_KEYS.length) {
    throw new Error(`expected ${SKILL_GROUP_KEYS.length} skill groups, found ${groupIndex}`);
  }
  return html;
}

function replaceLanguageState(html, language) {
  return html.replace(/<a\b[^>]*\bdata-lang="(en|de|lv)"[^>]*>/g, (tag, candidate) => {
    let next = tag.replace(/\s+aria-current="page"/g, "").replace(/\s+aria-pressed="[^"]*"/g, "");
    if (candidate === language) next = next.replace(/>$/, ' aria-current="page">');
    return next;
  });
}

function replaceMetaContent(html, keyAttribute, key, value) {
  const pattern = new RegExp(`(<meta\\s+${keyAttribute}="${escapeRegExp(key)}"\\s+content=")[^"]*("[^>]*>)`, "i");
  if (!pattern.test(html)) throw new Error(`missing meta ${keyAttribute}=${key}`);
  return html.replace(pattern, `$1${escapeHtml(value)}$2`);
}

function replaceCanonical(html, url) {
  const pattern = /<link rel="canonical" href="[^"]+">/;
  if (!pattern.test(html)) throw new Error("missing canonical link");
  return html.replace(pattern, `<link rel="canonical" href="${url}">`);
}

function replaceStructuredData(html, language, url, description, title) {
  const pattern = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/;
  const match = pattern.exec(html);
  if (!match) throw new Error("missing ProfilePage JSON-LD");
  const profile = JSON.parse(match[1]);
  profile["@id"] = `${url}#profile`;
  profile.url = url;
  profile.mainEntity.url = DEFAULT_URL;
  profile.mainEntity.jobTitle = title;
  profile.mainEntity.description = description;
  const serialized = JSON.stringify(profile).replaceAll("<", "\\u003c");
  return html.replace(pattern, `<script type="application/ld+json">${serialized}</script>`);
}

function localizedDescription(messages) {
  const role = String(messages.role || "").trim();
  const tagline = String(messages.tagline || "").trim();
  if (!role || !tagline) throw new Error("localized role/tagline missing");
  return `Andris Rožkalns — ${role} · Dortmund. ${tagline}`;
}

function titleFor(messages) {
  const role = String(messages.role || "").trim();
  const shortRole = role.startsWith("Junior ") ? role.slice("Junior ".length).trim() : role;
  if (!shortRole) throw new Error("localized role missing");
  return `Andris Rožkalns · ${shortRole}`;
}

function localizeLocation(html, language) {
  const country = new Intl.DisplayNames([LOCALES[language]], { type: "region", fallback: "code" }).of("DE") || "DE";
  const pattern = /(<span id="profileLocation"\b[^>]*>)([^<]*)(<\/span>)/;
  if (!pattern.test(html)) throw new Error("profile location binding missing");
  return html.replace(pattern, `$1Dortmund, ${escapeHtml(country)}$3`);
}

function localizePdf(html, language) {
  const pattern = /(<a\b[^>]*\bid="pdfLink"\b[^>]*\bhref=")[^"]*(")/;
  if (!pattern.test(html)) throw new Error("PDF link missing");
  return html.replace(pattern, `$1${PDFS[language]}$2`);
}

function renderPage(template, language, messages) {
  const url = `${ORIGIN}/${language}/`;
  const title = titleFor(messages);
  const description = localizedDescription(messages);
  let html = template;
  html = html.replace(/<html lang="[^"]+">/, `<html lang="${language}">`);
  html = replaceBoundText(html, messages);
  html = replaceBoundAttribute(html, "data-i18n-label", "aria-label", messages);
  html = replaceBoundAttribute(html, "data-i18n-placeholder", "placeholder", messages);
  html = replaceSkillChips(html, messages);
  html = localizeLocation(html, language);
  html = localizePdf(html, language);
  html = replaceLanguageState(html, language);
  html = html.replace(/<title>[\s\S]*?<\/title>/, `<title>${escapeHtml(title)}</title>`);
  html = replaceMetaContent(html, "name", "description", description);
  html = replaceMetaContent(html, "property", "og:title", title);
  html = replaceMetaContent(html, "property", "og:description", description);
  html = replaceMetaContent(html, "property", "og:url", url);
  html = replaceMetaContent(html, "name", "twitter:title", title);
  html = replaceMetaContent(html, "name", "twitter:description", description);
  html = replaceCanonical(html, url);
  html = replaceStructuredData(html, language, url, description, String(messages.role || ""));
  return html;
}

function sitemapXml() {
  const alternates = [
    ["en", `${ORIGIN}/en/`],
    ["de", `${ORIGIN}/de/`],
    ["lv", `${ORIGIN}/lv/`],
    ["x-default", DEFAULT_URL]
  ];
  const rows = LOCALIZED_LANGUAGES.map((language) => {
    const url = `${ORIGIN}/${language}/`;
    const links = alternates
      .map(([hreflang, href]) => `    <xhtml:link rel="alternate" hreflang="${hreflang}" href="${href}"/>`)
      .join("\n");
    return `  <url>\n    <loc>${url}</loc>\n${links}\n  </url>`;
  }).join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n${rows}\n</urlset>\n`;
}

export async function renderLocalizedPages({ root, htmlRoot }) {
  const template = await readFile(resolve(htmlRoot, "index.html"), "utf8");
  for (const language of LOCALIZED_LANGUAGES) {
    const messages = JSON.parse(
      await readFile(resolve(root, "content", "translations", `${language}.json`), "utf8")
    );
    const directory = resolve(htmlRoot, language);
    await mkdir(directory, { recursive: true });
    await writeFile(resolve(directory, "index.html"), renderPage(template, language, messages));
  }
  await writeFile(resolve(htmlRoot, "sitemap.xml"), sitemapXml());
  console.log(`FRONTEND_LOCALIZED_PAGES=${LOCALIZED_LANGUAGES.join(",")}`);
}
