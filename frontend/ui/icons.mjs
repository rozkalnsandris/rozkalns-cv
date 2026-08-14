const ICONS = Object.freeze({
  terminal: ["M4 5h16v14H4z", "m7 9 3 3-3 3", "M12 15h5"],
  container: ["m12 3 8 4-8 4-8-4 8-4Z", "m4 7 8 4 8-4", "M12 11v10", "m4 7v10l8 4 8-4V7"],
  network: ["M5 7h14", "M5 17h14", "M7 5v4", "M17 15v4", "M12 7v10"],
  shield: ["M12 3 19 6v5c0 4.5-2.8 7.7-7 10C7.8 18.7 5 15.5 5 11V6l7-3Z", "M9 12l2 2 4-5"],
  chart: ["M4 19V9", "M10 19V5", "M16 19v-7", "M22 19H2"],
  gear: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z", "M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"],
  branch: ["M6 3v12a4 4 0 0 0 4 4h4", "M14 5h4v4", "m18 5-4 4", "M6 3h.01"],
  code: ["M8 9 5 12 8 15", "M16 9 19 12 16 15", "M14 5 10 19"],
  home: ["m3 11 9-7 9 7", "M5 10v10h14V10", "M9 20v-6h6v6"],
  chip: ["M8 8h8v8H8z", "M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"],
  cloud: ["M7 18h10a4 4 0 0 0 .8-7.9A6 6 0 0 0 6.4 8.4 4.5 4.5 0 0 0 7 18Z"],
  database: ["M4 6c0 1.7 3.6 3 8 3s8-1.3 8-3-3.6-3-8-3-8 1.3-8 3Z", "M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6", "M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"],
  send: ["m22 2-7 20-4-9-9-4 20-7Z", "M11 13 22 2"],
  globe: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M3 12h18", "M12 3c2.5 2.5 3.5 5.5 3.5 9S14.5 18.5 12 21c-2.5-2.5-3.5-5.5-3.5-9S9.5 5.5 12 3Z"]
});

export function skillIconName(label) {
  const value = String(label || "").toLowerCase();
  if (/docker|compose/.test(value)) return "container";
  if (/chromadb|database|sqlite|postgres|mysql/.test(value)) return "database";
  if (/telegram/.test(value)) return "send";
  if (/adguard|safety|health check|ssl|tls|ssh|ftp/.test(value)) return "shield";
  if (/prometheus|grafana|node exporter|live metrics|energy/.test(value)) return "chart";
  if (/systemd|apt/.test(value)) return "gear";
  if (/git/.test(value)) return "branch";
  if (/python|php|html|css|yaml|bash|linux/.test(value)) {
    return value.includes("bash") || value.includes("linux") ? "terminal" : "code";
  }
  if (/home assistant/.test(value)) return "home";
  if (/raspberry pi|esp32|iot|matter|sensor|relay|multiplexer/.test(value)) return "chip";
  if (/ansible|terraform|aws|cloudflare|cloud/.test(value)) return "cloud";
  if (/dns|network|rest api|nginx|llm routing|mqtt/.test(value)) return "network";
  return "globe";
}

function createIcon(name, root) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = root.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  for (const d of ICONS[name] || ICONS.globe) {
    const path = root.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

function enhanceIconPill(element, root, { hideFallback = false } = {}) {
  if (!element.querySelector("svg")) {
    element.prepend(createIcon(skillIconName(element.textContent), root));
  }
  if (hideFallback) element.classList?.add?.("has-tech-icon");
}

export function enhanceSkillIcons(root = globalThis.document) {
  root.querySelectorAll(".skill-chip").forEach((chip) => {
    enhanceIconPill(chip, root);
  });
  root.querySelectorAll(".tech-tag").forEach((tag) => {
    enhanceIconPill(tag, root, { hideFallback: true });
  });
}
