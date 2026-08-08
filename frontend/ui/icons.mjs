const ICONS = Object.freeze({
  terminal: ["M4 5h16v14H4z", "m7 9 3 3-3 3", "M12 15h5"],
  container: ["m12 3 8 4-8 4-8-4 8-4Z", "m4 7 8 4 8-4", "M12 11v10", "m4 7v10l8 4 8-4V7"],
  network: ["M5 7h14", "M5 17h14", "M7 5v4", "M17 15v4", "M12 7v10"],
  shield: ["M12 3 19 6v5c0 4.5-2.8 7.7-7 10-4.2-2.3-7-10V6l7-3Z", "m9 12 2 2 4-5"],
  chart: ["M4 19V9", "M10 19V5", "M16 19v-7", "M22 19H2"],
  gear: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z", "M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"],
  branch: ["M6 3v12a4 4 0 0 0 4 4h4", "M14 5h4v4", "m18 5-4 4", "M6 3h.01"],
  code: ["m8 9-3 3 3-3 3", "m8-6 3 3-3 3", "m14 5-4 14"],
  home: ["m3 11 9-7 9 7", "M5 10v10h14V10", "M9 20v-6h6v6"],
  chip: ["M8 8h8v8H8z", "M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"],
  cloud: ["M7 18h10a4 4 0 0 0 .8-7.9A6 6 0 0 0 6.4 8.4 4.5 4.5 0 0 0 7 18Z"],
  globe: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M3 12h18", "M12 3c2.5 2.5 3.5 5.5 3.5 9S14.5 18.5 12 21c-2.5-2.5-3.5-5.5-3.5-9S9.5 5.5 12 3Z"]
});

export function skillIconName(label) {
  const value = String(label || "").toLowerCase();
  if (/docker|compose/.test(value)) return "container";
  if (/ssl|tls|ssh|ftp/.test(value)) return "shield";
  if (/prometheus|grafana/.test(value)) return "chart";
  if (/systemd/.test(value)) return "gear";
  if (/git/.test(value)) return "branch";
  if (/python|php|html|css|yaml|bash|linux/.test(value)) {
    return value.includes("bash") || value.includes("linux") ? "terminal" : "code";
  }
  if (/home assistant/.test(value)) return "home";
  if (/esp32|iot/.test(value)) return "chip";
  if (/ansible|terraform|aws|cloud/.test(value)) return "cloud";
  if (/dns|network|rest api|nginx/.test(value)) return "network";
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

export function enhanceSkillIcons(root = globalThis.document) {
  root.querySelectorAll(".skill-chip").forEach((chip) => {
    if (chip.querySelector("svg")) return;
    chip.prepend(createIcon(skillIconName(chip.textContent), root));
  });
}
