import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const LANGUAGES = Object.freeze(["en", "de", "lv"]);
const LEVELS = Object.freeze(["core", "working", "foundations", "learning"]);
const PROJECT_SLOT = '<div class="proof-grid" data-engineering-proof-projects></div>';

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function validateEvidenceUrl(url, allowedHosts, evidenceId) {
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error(`unsafe engineering proof URL for ${evidenceId}`);
  }
  if (!allowedHosts.has(parsed.hostname)) {
    throw new Error(`unapproved engineering proof host for ${evidenceId}: ${parsed.hostname}`);
  }
  if (parsed.hostname === "github.com" && !/^\/[^/]+\/[^/]+\/blob\/main\/.+/.test(parsed.pathname)) {
    throw new Error(`engineering proof GitHub URL must use a stable main-branch file path: ${evidenceId}`);
  }
}

function evidenceLabel(item) {
  const name = item.path.split("/").filter(Boolean).at(-1);
  if (!name) throw new Error(`engineering proof evidence path has no filename: ${item.path}`);
  return name;
}

function translationKeys(project, englishMessages) {
  const matches = Object.entries(englishMessages).filter(
    ([key, value]) => /^p[0-9]+_title$/.test(key) && value === project.title
  );
  if (matches.length !== 1) {
    throw new Error(`canonical project title must map to exactly one translation title: ${project.id}`);
  }
  const titleKey = matches[0][0];
  const prefix = titleKey.slice(0, -"_title".length);
  const summaryKey = `${prefix}_desc`;
  const operationsKey = `${prefix}_ops`;
  if (typeof englishMessages[summaryKey] !== "string") {
    throw new Error(`canonical project is missing localized summary: ${project.id}`);
  }
  return {
    titleKey,
    summaryKey,
    operationsKey: typeof englishMessages[operationsKey] === "string" ? operationsKey : null,
  };
}

function projectEvidence(registry, projectId, allowedHosts) {
  return Object.entries(registry.evidence).filter(([_id, item]) => {
    const projectIds = Array.isArray(item.project_ids) ? item.project_ids : [];
    return projectIds.includes(projectId);
  }).map(([evidenceId, item]) => {
    validateEvidenceUrl(item.url, allowedHosts, evidenceId);
    return { evidenceId, item };
  });
}

function projectSkills(profile, registry, evidenceIds, skillLabels, englishMessages) {
  const rows = [];
  for (const level of LEVELS) {
    for (const concept of profile.skills[level] || []) {
      const mapped = registry.skill_evidence[concept] || [];
      if (!mapped.some((evidenceId) => evidenceIds.has(evidenceId))) continue;
      const label = skillLabels.labels?.[concept]?.en;
      const levelLabel = englishMessages[`skills_${level}`];
      if (typeof label !== "string" || typeof levelLabel !== "string") {
        throw new Error(`engineering proof skill localization is incomplete: ${concept}`);
      }
      rows.push({ concept, level, label, levelLabel });
    }
  }
  return rows;
}

function renderProjectCard({ project, index, keys, evidenceRows, skills }) {
  const operations = keys.operationsKey
    ? `<div class="proof-field"><h4 data-proof-i18n="operations_label">Operations</h4><p data-i18n="${escapeHtml(keys.operationsKey)}"></p></div>`
    : "";
  const skillHtml = skills.map(({ concept, level, label, levelLabel }) =>
    `<span class="proof-skill"><span class="proof-skill-name" data-proof-skill="${escapeHtml(concept)}">${escapeHtml(label)}</span><small class="proof-skill-level" data-proof-level="${escapeHtml(level)}">${escapeHtml(levelLabel)}</small></span>`
  ).join("");
  const linkHtml = evidenceRows.map(({ evidenceId, item }) =>
    `<a class="tech-tag github-row proof-evidence-link" data-proof-evidence-id="${escapeHtml(evidenceId)}" href="${escapeHtml(item.url)}">${escapeHtml(evidenceLabel(item))}</a>`
  ).join("");
  return `<article class="proof-project panel" data-proof-project-id="${escapeHtml(project.id)}"><header class="proof-project-head"><span class="proof-project-index">${String(index + 1).padStart(2, "0")}</span><h3 data-i18n="${escapeHtml(keys.titleKey)}"></h3></header><div class="proof-project-body"><div class="proof-field"><h4 data-proof-i18n="summary_label">What it shows</h4><p data-i18n="${escapeHtml(keys.summaryKey)}"></p></div>${operations}<div class="proof-field"><h4 data-proof-i18n="skills_label">Technologies &amp; proficiency</h4><div class="proof-skills">${skillHtml}</div></div><div class="proof-field"><h4 data-proof-i18n="evidence_label">Public evidence</h4><div class="proof-links">${linkHtml}</div></div></div></article>`;
}

function replaceHrefById(html, id, href) {
  const tagPattern = new RegExp(`<a\\b(?=[^>]*\\bid="${id}")[^>]*>`, "i");
  const tag = tagPattern.exec(html)?.[0];
  if (!tag) throw new Error(`${id} link is missing from engineering proof template`);
  if (!/\bhref="[^"]*"/i.test(tag)) throw new Error(`${id} link has no href`);
  return html.replace(tag, tag.replace(/\bhref="[^"]*"/i, `href="${escapeHtml(href)}"`));
}

export async function bindEngineeringProof({ root, htmlPath }) {
  const [config, profile, registry, skillLabels, englishMessages] = await Promise.all([
    readFile(resolve(root, "content", "proof.json"), "utf8").then(JSON.parse),
    readFile(resolve(root, "content", "profile.json"), "utf8").then(JSON.parse),
    readFile(resolve(root, "content", "evidence.json"), "utf8").then(JSON.parse),
    readFile(resolve(root, "content", "skill-labels.json"), "utf8").then(JSON.parse),
    readFile(resolve(root, "content", "translations", "en.json"), "utf8").then(JSON.parse),
  ]);
  if (config.schema_version !== 1 || config.canonical_profile !== "content/profile.json" || config.canonical_evidence !== "content/evidence.json" || config.canonical_skill_labels !== "content/skill-labels.json") {
    throw new Error("engineering proof canonical source contract is invalid");
  }
  if (!LANGUAGES.every((language) => config.i18n?.[language])) {
    throw new Error("engineering proof localization is incomplete");
  }
  const projectIds = config.featured_project_ids;
  if (!Array.isArray(projectIds) || projectIds.length < 3 || projectIds.length > 5 || new Set(projectIds).size !== projectIds.length) {
    throw new Error("engineering proof must select 3-5 unique canonical projects");
  }
  const canonicalProjects = new Map(profile.projects.map((project) => [project.id, project]));
  const allowedHosts = new Set(registry.policy.allowed_url_hosts);
  const cards = projectIds.map((projectId, index) => {
    const project = canonicalProjects.get(projectId);
    if (!project) throw new Error(`engineering proof references unknown canonical project: ${projectId}`);
    const evidenceRows = projectEvidence(registry, projectId, allowedHosts);
    if (evidenceRows.length === 0) throw new Error(`engineering proof project has no public evidence: ${projectId}`);
    const evidenceIds = new Set(evidenceRows.map(({ evidenceId }) => evidenceId));
    const skills = projectSkills(profile, registry, evidenceIds, skillLabels, englishMessages);
    if (skills.length === 0) throw new Error(`engineering proof project has no evidenced canonical skills: ${projectId}`);
    return renderProjectCard({ project, index, keys: translationKeys(project, englishMessages), evidenceRows, skills });
  });
  const lesson = registry.evidence[config.lesson_evidence_id];
  if (!lesson) throw new Error("engineering proof lesson evidence is missing from canonical registry");
  validateEvidenceUrl(lesson.url, allowedHosts, config.lesson_evidence_id);
  let html = await readFile(htmlPath, "utf8");
  if (html.split(PROJECT_SLOT).length !== 2) throw new Error("engineering proof project slot is missing or duplicated");
  html = html.replace(PROJECT_SLOT, `<div class="proof-grid" data-engineering-proof-projects>${cards.join("")}</div>`);
  html = replaceHrefById(html, "proofLessonLink", lesson.url);
  await writeFile(htmlPath, html);
  console.log(`FRONTEND_ENGINEERING_PROOF=${projectIds.join(",")}`);
}
