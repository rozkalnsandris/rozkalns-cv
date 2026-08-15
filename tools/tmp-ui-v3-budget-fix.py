from pathlib import Path

root = Path(__file__).resolve().parents[1]
index_path = root / "frontend" / "index.html"
layout_path = root / "frontend" / "styles" / "layout.css"

text = index_path.read_text(encoding="utf-8")
replacements = {
    '<section id="about" class="v3-section v3-about">': '<section id="about">',
    '<section id="projects" class="v3-section v3-projects">': '<section id="projects">',
    '<section id="skills" class="v3-section v3-skills">': '<section id="skills">',
    '<section id="experience" class="v3-section v3-experience">': '<section id="experience">',
    '<section id="stats" class="v3-section v3-stats">': '<section id="stats">',
    '<section id="education" class="v3-section v3-education">': '<section id="education">',
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f"missing compactable marker: {old}")
    text = text.replace(old, new, 1)
index_path.write_text(text, encoding="utf-8")

layout = layout_path.read_text(encoding="utf-8")
marker = ".v3-section { min-width: 0; }\n"
if layout.count(marker) != 1:
    raise SystemExit("v3 section CSS marker missing")
layout_path.write_text(layout.replace(marker, "", 1), encoding="utf-8")
print("UI_V3_BUDGET_FIX=PASS")
