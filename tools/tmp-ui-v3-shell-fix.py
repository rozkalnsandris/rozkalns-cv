from pathlib import Path

path = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
text = path.read_text(encoding="utf-8")
old = '<a class="brand" href="./" aria-label="Andris Rožkalns">AR</a>'
new = '<span class="brand" aria-hidden="true">AR</span>'
if text.count(old) != 1:
    raise SystemExit("UI v3 brand anchor marker missing")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("UI_V3_BRAND_FIX=PASS")
