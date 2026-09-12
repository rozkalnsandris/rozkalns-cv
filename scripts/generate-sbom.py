#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PY_LOCK = ROOT / "bot" / "requirements.txt"
PY_DIRECT = ROOT / "bot" / "requirements.in"
NODE_LOCK = ROOT / "package-lock.json"
OUT_PY = ROOT / "security" / "sbom-python.cdx.json"
OUT_NODE = ROOT / "security" / "sbom-node.cdx.json"


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def python_bom() -> dict:
    text = PY_LOCK.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)(?=^[A-Za-z0-9][A-Za-z0-9_.-]*==)", text)
    packages: dict[str, tuple[str, list[str]]] = {}
    parents: dict[str, set[str]] = {}
    for block in blocks:
        m = re.match(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", block)
        if not m:
            continue
        name, version = norm(m.group(1)), m.group(2)
        via: list[str] = []
        lines = block.splitlines()
        collecting = False
        for line in lines:
            stripped = line.strip()
            if stripped == "# via":
                collecting = True
                continue
            if stripped.startswith("# via "):
                token = stripped[6:].strip()
                if not token.startswith("-r "):
                    via.append(norm(token))
                collecting = False
                continue
            if collecting:
                if not stripped.startswith("#"):
                    collecting = False
                    continue
                token = stripped[1:].strip()
                if token and not token.startswith("-r "):
                    via.append(norm(token))
        packages[name] = (version, via)
        parents[name] = set(via)
    direct = []
    for line in PY_DIRECT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        direct.append(norm(line.split("==", 1)[0]))
    components = [
        {"type": "library", "name": name, "version": version,
         "bom-ref": f"pkg:pypi/{name}@{version}",
         "purl": f"pkg:pypi/{name}@{version}"}
        for name, (version, _) in sorted(packages.items())
    ]
    children: dict[str, set[str]] = {name: set() for name in packages}
    for child, ps in parents.items():
        for parent in ps:
            if parent in children:
                children[parent].add(child)
    deps = [{"ref": "urn:rozkalns-cv:python", "dependsOn": [f"pkg:pypi/{n}@{packages[n][0]}" for n in sorted(direct)]}]
    deps += [{"ref": f"pkg:pypi/{name}@{version}", "dependsOn": [f"pkg:pypi/{c}@{packages[c][0]}" for c in sorted(children[name])]}
             for name, (version, _) in sorted(packages.items())]
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "metadata": {"component": {"type": "application", "name": "rozkalns-cv-cvbot-python", "bom-ref": "urn:rozkalns-cv:python"},
                         "properties": [{"name": "rozkalns:source-lock", "value": "bot/requirements.txt"}]},
            "components": components, "dependencies": deps}


def node_name(path: str, record: dict) -> str:
    if record.get("name"):
        return record["name"]
    return path.rsplit("node_modules/", 1)[-1]


def node_bom() -> dict:
    lock = json.loads(NODE_LOCK.read_text(encoding="utf-8"))
    if lock.get("lockfileVersion") != 3:
        raise ValueError("package-lock.json must use lockfileVersion 3")
    rows = {}
    for path, rec in lock.get("packages", {}).items():
        if not path:
            continue
        name, version = node_name(path, rec), rec.get("version")
        if not version:
            raise ValueError(f"missing npm version for {path}")
        rows[path] = (name, version, rec)
    by_name: dict[str, list[str]] = {}
    for path, (name, _, _) in rows.items():
        by_name.setdefault(name, []).append(path)
    def resolve(parent_path: str, dep_name: str) -> str | None:
        probe = parent_path
        while True:
            candidate = f"{probe}/node_modules/{dep_name}" if probe else f"node_modules/{dep_name}"
            if candidate in rows:
                return candidate
            if "/node_modules/" not in probe:
                break
            probe = probe.rsplit("/node_modules/", 1)[0]
        choices = by_name.get(dep_name, [])
        return choices[0] if len(choices) == 1 else None
    def ref(path: str) -> str:
        name, version, _ = rows[path]
        return f"pkg:npm/{name.replace('@','%40')}@{version}"
    components = []
    dependencies = []
    for path in sorted(rows):
        name, version, rec = rows[path]
        component = {"type": "library", "name": name, "version": version, "bom-ref": ref(path), "purl": ref(path)}
        if rec.get("dev"):
            component["scope"] = "excluded"
        components.append(component)
        names = set((rec.get("dependencies") or {})) | set((rec.get("optionalDependencies") or {}))
        refs = []
        for dep in sorted(names):
            target = resolve(path, dep)
            if target:
                refs.append(ref(target))
        dependencies.append({"ref": ref(path), "dependsOn": sorted(set(refs))})
    root = lock.get("packages", {}).get("", {})
    roots = []
    for dep in sorted(set(root.get("dependencies", {})) | set(root.get("devDependencies", {}))):
        target = resolve("", dep)
        if target:
            roots.append(ref(target))
    dependencies.insert(0, {"ref": "urn:rozkalns-cv:node", "dependsOn": roots})
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "metadata": {"component": {"type": "application", "name": root.get("name", "rozkalns-cv-frontend"), "bom-ref": "urn:rozkalns-cv:node"},
                         "properties": [{"name": "rozkalns:source-lock", "value": "package-lock.json"}]},
            "components": components, "dependencies": dependencies}


def encoded(doc: dict) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = [(OUT_PY, encoded(python_bom())), (OUT_NODE, encoded(node_bom()))]
    stale = []
    for path, data in outputs:
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != data:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(data, encoding="utf-8")
    if stale:
        print("SBOM_CHECK=FAIL stale=" + ",".join(stale), file=sys.stderr)
        return 1
    print("SBOM_CHECK=PASS" if args.check else "SBOM_GENERATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
