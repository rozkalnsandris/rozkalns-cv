from pathlib import Path

path = Path("tests/browser-smoke.mjs")
text = path.read_text(encoding="utf-8")
old = '''    await this.send("Input.dispatchKeyEvent", {
      type: "rawKeyDown",
      ...keyParams
    });'''
new = '''    await this.send("Input.dispatchKeyEvent", {
      type: key === "Enter" ? "keyDown" : "rawKeyDown",
      ...(key === "Enter" ? { text: "\\r", unmodifiedText: "\\r" } : {}),
      ...keyParams
    });'''
if text.count(old) != 1:
    raise SystemExit("C6 browser keyDown anchor drift")
path.write_text(text.replace(old, new), encoding="utf-8")
print("C6_TRUSTED_ENTER_SYNTHESIS=PASS")
