import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const PROOF_SLOT = /<span data-proof-projects="([^"]+)" data-proof-evidence-ids="([^"]+)"><\/span>/g;

function tokens(value, label) {
  const items = value.split(/\s+/).filter(Boolean);
  if (items.length === 0 || new Set(items).size !== items.length) {
    throw new Error(`invalid ${label}: ${value}`);
  }
  return items;
}

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
    throw new Error(`unsafe evidence URL for ${evidenceId}`);
  }
  if (!allowedHosts.has(parsed.hostname)) {
    throw new Error(`unapproved evidence host for ${evidenceId}: ${parsed.hostname}`);
  }
  if (parsed.hostname === "github.com" && !/^\/[^/]+\/[^/]+\/blob\/main\/.+/.test(parsed.pathname)) {
    throw new Error(`GitHub proof must use a stable main-branch file path: ${evidenceId}`);
  }
}

function evidenceLabel(item) {
  const name = item.path.split("/").filter(Boolean).at(-1);
  if (!name) throw new Error(`evidence path has no filename: ${item.path}`);
  return name;
}

export async function bindProjectProof({ root, htmlPath }) {
  const [registry, profile] = await Promise.all([
    readFile(resolve(root, "content", "evidence.json"), "utf8").then(JSON.parse),
    readFile(resolve(root, "content", "profile.json"), "utf8").then(JSON.parse)
  ]);
  const canonicalProjects = new Set(profile.projects.map((project) => project.id));
  const allowedHosts = new Set(registry.policy.allowed_url_hosts);
  const featuredProjects = new Set();
  let html = await readFile(htmlPath, "utf8");
  let replacements = 0;

  html = html.replace(PROOF_SLOT, (_slot, projectText, evidenceText) => {
    const projectIds = tokens(projectText, "proof project ids");
    const evidenceIds = tokens(evidenceText, "proof evidence ids");
    const coveredProjects = new Set();
    const links = evidenceIds.map((evidenceId) => {
      const item = registry.evidence[evidenceId];
      if (!item) throw new Error(`undefined proof evidence id: ${evidenceId}`);
      validateEvidenceUrl(item.url, allowedHosts, evidenceId);
      const linkedProjects = new Set(item.project_ids);
      if (![...linkedProjects].some((projectId) => projectIds.includes(projectId))) {
        throw new Error(`proof evidence ${evidenceId} does not support its featured project slot`);
      }
      for (const projectId of projectIds) {
        if (linkedProjects.has(projectId)) coveredProjects.add(projectId);
      }
      return `<a class="tech-tag github-row project-proof-link" data-proof-evidence-id="${escapeHtml(evidenceId)}" href="${escapeHtml(item.url)}">${escapeHtml(evidenceLabel(item))} ↗</a>`;
    });
    for (const projectId of projectIds) {
      if (!canonicalProjects.has(projectId)) throw new Error(`unknown canonical project id: ${projectId}`);
      if (!coveredProjects.has(projectId)) throw new Error(`featured project has no selected proof: ${projectId}`);
      featuredProjects.add(projectId);
    }
    replacements += 1;
    return links.join("");
  });

  if (replacements === 0) throw new Error("no project proof slots found");
  if (featuredProjects.size < 3 || featuredProjects.size > 5) {
    throw new Error(`project proof must cover 3-5 canonical projects, found ${featuredProjects.size}`);
  }
  await writeFile(htmlPath, html);
  console.log(`FRONTEND_PROJECT_PROOF=${[...featuredProjects].sort().join(",")}`);
}
