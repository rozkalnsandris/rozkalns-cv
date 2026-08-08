#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0 and new in text:
        return text
    if count != 1:
        raise SystemExit(f"{label}: expected one old block, found {count}")
    return text.replace(old, new, 1)


def rewrite_build_content() -> None:
    path = ROOT / "scripts" / "build-content.py"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'^HASH_RE = re\.compile\(.+\)\n', '', text, flags=re.M)
    if "def replace_exactly_once(" in text:
        text, count = re.subn(
            r'\ndef replace_exactly_once\(.*?\n\ndef expected_pdf_manifest',
            '\n\ndef expected_pdf_manifest',
            text,
            count=1,
            flags=re.S,
        )
        if count != 1:
            raise SystemExit("build-content: could not remove manual frontend fingerprint helpers")

    start = text.index("def check_or_write(args: argparse.Namespace) -> None:\n")
    end = text.index("\n\ndef main() -> None:", start)
    new = '''def check_or_write(args: argparse.Namespace) -> None:\n    profile = load_profile()\n    validate_profile(profile)\n    translations, _raw_translations = load_translations()\n    validate_translations(translations)\n    source_sha256 = source_digest(profile, translations)\n    manifest = expected_pdf_manifest(profile, source_sha256)\n\n    expected_files = {\n        BOT_PROMPT_PATH: build_system_prompt(profile, source_sha256),\n    }\n    for filename, content in expected_files.items():\n        if not content.endswith("\\n"):\n            raise SourceError(f"generated file must end with newline: {filename}")\n\n    if args.write:\n        for path, content in expected_files.items():\n            atomic_write(path, content)\n    else:\n        for path, expected in expected_files.items():\n            assert_generated_file(path, expected)\n\n    if not args.skip_pdf_manifest:\n        if args.write_pdf_manifest:\n            atomic_write(PDF_MANIFEST_PATH, canonical_json(manifest) + "\\n")\n        else:\n            assert_pdf_manifest(manifest)\n\n    print(f"CONTENT_SOURCE_SHA256={source_sha256}")\n    print("CONTENT_BUILD=PASS")\n'''
    text = text[:start] + new + text[end:]
    path.write_text(text, encoding="utf-8")


def rewrite_validate_source() -> None:
    path = ROOT / "scripts" / "validate-source.sh"
    text = path.read_text(encoding="utf-8")
    old_allowed = '''  .gitignore\n  README.md\n  content\n  docker-compose.yml\n  html\n  nginx.conf\n  scripts\n  security\n  tests\n)'''
    new_allowed = '''  .gitignore\n  README.md\n  content\n  docker-compose.yml\n  frontend\n  frontend-dist-manifest.json\n  html\n  nginx.conf\n  package-lock.json\n  package.json\n  scripts\n  security\n  tests\n  vite.config.mjs\n)'''
    text = replace_once(text, old_allowed, new_allowed, "validate-source allowed paths")
    old_required = '''  "html/index.html"\n  "html/smarthome.html"\n  "html/assets/app.d878d409f278.mjs"\n  "html/assets/enhancements.0027f066ac26.mjs"\n  "html/assets/smarthome.70da56476fdb.mjs"\n  "html/assets/main.8548550e57d3.css"\n  "html/assets/extra.d1b655894a50.css"'''
    new_required = '''  "frontend/index.html"\n  "frontend/smarthome.html"\n  "frontend/app.mjs"\n  "frontend/enhancements.mjs"\n  "frontend/smarthome.mjs"\n  "frontend/styles/main.css"\n  "frontend/styles/extra.css"\n  "frontend-dist-manifest.json"\n  "package.json"\n  "package-lock.json"\n  "vite.config.mjs"\n  "html/index.html"\n  "html/smarthome.html"'''
    text = replace_once(text, old_required, new_required, "validate-source required frontend")
    path.write_text(text, encoding="utf-8")


def rewrite_ci() -> None:
    path = ROOT / ".github" / "workflows" / "ci.yml"
    text = path.read_text(encoding="utf-8")
    old_frontend = '''      - name: Validate frontend modules and behavior\n        shell: bash\n        run: |\n          set -Eeuo pipefail\n          node --check html/assets/app.d878d409f278.mjs\n          node --check html/assets/smarthome.70da56476fdb.mjs\n          node --check tests/browser-smoke.mjs\n          node --test tests/frontend.test.mjs\n          bash scripts/validate-source.sh "$PWD"\n\n'''
    new_frontend = '''      - name: Set up pinned Node.js frontend toolchain\n        uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0\n        with:\n          node-version: '24.18.0'\n          package-manager-cache: false\n\n      - name: Rebuild deterministic frontend dist from authoritative source\n        shell: bash\n        run: |\n          set -Eeuo pipefail\n          npm ci --ignore-scripts --no-audit --no-fund\n          npm run build:frontend\n          first="${RUNNER_TEMP}/frontend-first.sha256"\n          second="${RUNNER_TEMP}/frontend-second.sha256"\n          {\n            find html/assets html/i18n -type f -print0\n            printf '%s\\0' html/index.html html/smarthome.html frontend-dist-manifest.json\n          } | sort -z | xargs -0 sha256sum > "$first"\n          npm run build:frontend\n          {\n            find html/assets html/i18n -type f -print0\n            printf '%s\\0' html/index.html html/smarthome.html frontend-dist-manifest.json\n          } | sort -z | xargs -0 sha256sum > "$second"\n          cmp "$first" "$second"\n          npm run check:frontend\n          git diff --exit-code -- \
            package-lock.json frontend-dist-manifest.json \
            html/assets html/i18n html/index.html html/smarthome.html\n          printf 'FRONTEND_DOUBLE_BUILD_DETERMINISTIC=PASS\\n'\n\n      - name: Validate frontend source modules and behavior\n        shell: bash\n        run: |\n          set -Eeuo pipefail\n          node --check frontend/app.mjs\n          node --check frontend/enhancements.mjs\n          node --check frontend/smarthome.mjs\n          node --check scripts/build-frontend.mjs\n          node --check scripts/check-frontend-dist.mjs\n          node --check tests/browser-smoke.mjs\n          node --test tests/frontend.test.mjs\n          npm run check:frontend\n\n'''
    text = replace_once(text, old_frontend, new_frontend, "CI frontend block")

    old_module = '''          module_path="$(grep -oE '/assets/app\\.[0-9a-f]{12}\\.mjs\\?cfg=[0-9a-f]{12}' \\\n            html/index.html | head -n 1)"\n          test -n "$module_path"\n'''
    new_module = '''          module_path="$(python3 - <<'PY'\n          import json\n          from pathlib import Path\n          manifest = json.loads(Path('frontend-dist-manifest.json').read_text(encoding='utf-8'))\n          path = manifest.get('index.html', {}).get('file', '')\n          if not re.fullmatch(r'assets/app\\.[0-9a-f]{12}\\.mjs', path):\n              raise SystemExit(f'unexpected app entry: {path!r}')\n          print('/' + path)\n          PY\n          )"\n          test -n "$module_path"\n'''
    # Keep the embedded Python import self-contained.
    new_module = new_module.replace("          import json\n", "          import json\n          import re\n")
    text = replace_once(text, old_module, new_module, "CI nginx module lookup")

    old_clean = '''          rm -f cloudflared.env bot/.env\n          bash scripts/validate-source.sh "$PWD"'''
    new_clean = '''          rm -f cloudflared.env bot/.env\n          rm -rf node_modules\n          bash scripts/validate-source.sh "$PWD"'''
    text = replace_once(text, old_clean, new_clean, "CI final clean source")
    text = text.replace(
        "frontend module behavior, translation parity, content hashes and size budgets",
        "frontend source behavior, Vite manifest integrity, deterministic rebuilds and size budgets",
    )
    path.write_text(text, encoding="utf-8")


rewrite_build_content()
rewrite_validate_source()
rewrite_ci()
print("C2_REWRITE=PASS")
