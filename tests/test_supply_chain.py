from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "bot" / "Dockerfile"
COMPOSE = ROOT / "docker-compose.yml"
DIRECT = ROOT / "bot" / "requirements.in"
LOCK = ROOT / "bot" / "requirements.txt"
LEGACY_LOCK = ROOT / "bot" / "requirements.lock"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
SUPPLY = ROOT / "security" / "supply-chain.json"
HELPER = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"
CI = ROOT / ".github" / "workflows" / "ci.yml"
GITLEAKS_IGNORE = ROOT / ".gitleaksignore"


def load_build_module():
    path = ROOT / "scripts" / "build-input-id.py"
    spec = importlib.util.spec_from_file_location("build_input_id", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def direct_requirements() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for raw in DIRECT.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s]+)", line)
        if match is None:
            raise AssertionError(f"direct dependency is not an exact pin: {line!r}")
        rows.append((match.group(1).lower().replace("_", "-"), match.group(2)))
    return rows


class SupplyChainContractTests(unittest.TestCase):
    def test_direct_dependencies_are_exact_and_bounded(self) -> None:
        rows = direct_requirements()
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {name for name, _ in rows},
            {"flask", "requests", "gunicorn"},
        )

    def test_lock_is_hash_complete_and_matches_direct_dependencies(self) -> None:
        self.assertFalse(LEGACY_LOCK.exists())
        text = LOCK.read_text(encoding="utf-8")
        self.assertIn("--output-file=bot/requirements.txt", text)
        self.assertNotIn("--trusted-host", text)
        self.assertNotIn("-e ", text)
        rows = re.findall(r"(?m)^([a-z0-9][a-z0-9_.-]*)==([^\\\s]+)", text)
        self.assertGreaterEqual(len(rows), 10)
        packages = {name.replace("_", "-"): version for name, version in rows}
        direct = dict(direct_requirements())
        self.assertEqual({name: packages.get(name) for name in direct}, direct)
        blocks = re.split(r"(?m)(?=^[a-z0-9][a-z0-9_.-]*==)", text)
        package_blocks = [block for block in blocks if re.match(r"^[a-z0-9]", block)]
        self.assertEqual(len(package_blocks), len(rows))
        for block in package_blocks:
            self.assertRegex(block, r"--hash=sha256:[0-9a-f]{64}")

    def test_python_dependabot_tracks_bot_manifest(self) -> None:
        text = DEPENDABOT.read_text(encoding="utf-8")
        matches = re.findall(
            r'(?ms)^  - package-ecosystem: "pip"\n(.*?)(?=^  - package-ecosystem:|\Z)',
            text,
        )
        self.assertEqual(len(matches), 1)
        block = matches[0]
        self.assertIn('    directory: "/bot"', block)
        self.assertIn('      interval: "weekly"', block)
        self.assertIn("    open-pull-requests-limit: 2", block)

    def test_runtime_images_are_immutable_and_audited(self) -> None:
        compose = COMPOSE.read_text(encoding="utf-8")
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        manifest = json.loads(SUPPLY.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        images = manifest["images"]
        expected = {
            "python:3.12.13-alpine3.24",
            "nginx:1.31.4-alpine",
            "aquasec/trivy:0.72.0",
            "ghcr.io/gitleaks/gitleaks:v8.30.0",
        }
        self.assertEqual(set(images), expected)
        self.assertNotIn("cloudflare/cloudflared:2026.7.3", images)
        for reference, digest in images.items():
            self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")
            if reference.startswith("python:"):
                self.assertIn(f"FROM {reference}@{digest}", dockerfile)
            elif reference == "nginx:1.31.4-alpine":
                self.assertIn(f"image: {reference}@{digest}", compose)
        self.assertNotIn("cloudflare/cloudflared", compose)
        self.assertNotIn(":latest", compose)
        self.assertNotIn("FROM python:3.12\n", dockerfile)

    def test_cvbot_is_non_root_read_only_and_capability_free(self) -> None:
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        compose = COMPOSE.read_text(encoding="utf-8")
        self.assertIn("USER ${APP_UID}:${APP_GID}", dockerfile)
        self.assertIn('user: "10001:10001"', compose)
        self.assertIn("read_only: true", compose)
        self.assertRegex(compose, r"cap_drop:\s*\n\s*- ALL")
        self.assertIn("no-new-privileges:true", compose)
        self.assertIn("pids_limit: 128", compose)
        self.assertIn("/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777", compose)
        self.assertIn("./bot/data:/app/data:rw", compose)
        self.assertNotIn("/var/run/docker.sock", compose)

    def test_build_uses_hashes_and_traceable_labels(self) -> None:
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        compose = COMPOSE.read_text(encoding="utf-8")
        ci = CI.read_text(encoding="utf-8")
        self.assertIn("COPY requirements.txt ./requirements.txt", dockerfile)
        self.assertIn("--require-hashes --no-deps -r requirements.txt", dockerfile)
        self.assertNotIn("requirements.lock", dockerfile)
        self.assertIn("-r bot/requirements.txt", ci)
        self.assertNotIn("bot/requirements.lock", ci)
        self.assertIn('org.opencontainers.image.revision="${VCS_REF}"', dockerfile)
        self.assertIn(
            'net.rozkalns.cv.build-input-sha256="${BUILD_INPUT_SHA256}"',
            dockerfile,
        )
        self.assertIn("VCS_REF: ${CVBOT_VCS_REF:-unresolved}", compose)
        self.assertIn(
            "BUILD_INPUT_SHA256: ${CVBOT_BUILD_INPUT_SHA256:-unresolved}",
            compose,
        )
        self.assertIn("image: rozkalns-cv-cvbot:${CVBOT_VCS_REF:-local}", compose)
        self.assertIn("pull_policy: never", compose)

    def test_build_input_identifier_is_deterministic_and_content_sensitive(self) -> None:
        module = load_build_module()
        first, rows = module.calculate(ROOT)
        second, repeated_rows = module.calculate(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(rows, repeated_rows)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        expected_paths = set(module.INPUTS)
        self.assertEqual({path for path, _ in rows}, expected_paths)
        self.assertIn("bot/requirements.txt", expected_paths)
        self.assertNotIn("bot/requirements.lock", expected_paths)
        digest = hashlib.sha256()
        for relative, _ in rows:
            content = (ROOT / relative).read_bytes()
            encoded = relative.encode("utf-8")
            digest.update(len(encoded).to_bytes(4, "big"))
            digest.update(encoded)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
        self.assertEqual(first, digest.hexdigest())

    def test_deploy_migrates_private_data_and_verifies_image_identity(self) -> None:
        helper = HELPER.read_text(encoding="utf-8")
        self.assertIn("CVBOT_UID=10001", helper)
        self.assertIn("CVBOT_GID=10001", helper)
        self.assertIn("prepare_cvbot_data", helper)
        self.assertIn('chown -R -- "$CVBOT_UID:$CVBOT_GID"', helper)
        self.assertIn('find "$data_dir" -type l', helper)
        self.assertIn('CVBOT_VCS_REF="$TARGET_SHA"', helper)
        self.assertIn("CVBOT_BUILD_INPUT_SHA256", helper)
        self.assertIn("org.opencontainers.image.revision", helper)
        self.assertIn("net.rozkalns.cv.build-input-sha256", helper)
        self.assertIn('image_ref="rozkalns-cv-cvbot:${CVBOT_VCS_REF}"', helper)
        self.assertNotIn("compose_runtime images -q cvbot", helper)
        self.assertLess(
            helper.index("verify_cvbot_image_identity || return 1"),
            helper.index("compose_runtime up -d --no-deps cvbot || return 1"),
        )

    def test_ci_runs_canary_fixture_matrix_history_and_vulnerability_scans(self) -> None:
        ci = CI.read_text(encoding="utf-8")
        gitleaks = (ROOT / "scripts" / "run-gitleaks.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("scripts/run-gitleaks.sh", ci)
        self.assertIn("fetch --no-tags --prune origin", ci)
        self.assertIn("+refs/heads/*:refs/remotes/origin/*", ci)
        self.assertIn('fetch --no-tags origin "$GITHUB_SHA"', ci)
        self.assertIn("rev-parse --is-shallow-repository", ci)
        self.assertIn("--all", gitleaks)
        self.assertIn("GITLEAKS_CANARY=PASS", gitleaks)
        self.assertIn("GITLEAKS_FIXTURE_MATRIX=PASS", gitleaks)
        for fixture_name in (
            "cloudflare_tunnel",
            "cloudflare_api",
            "aws",
            "private_key",
            "webhook",
            "jwt",
            "password",
            "database_url",
            "high_entropy",
        ):
            self.assertIn(fixture_name, gitleaks)
        self.assertIn("v8.30.0@sha256:691af3c7", gitleaks)
        self.assertNotIn("v8.30.1", gitleaks)
        self.assertIn('image_ref="rozkalns-cv-cvbot:${CVBOT_VCS_REF}"', ci)
        self.assertIn("trivy", ci.lower())
        self.assertIn("HIGH,CRITICAL", ci)
        self.assertIn("--exit-code 1", ci)

    def test_gitleaks_baseline_is_exact_and_non_broad(self) -> None:
        lines = GITLEAKS_IGNORE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            lines,
            [
                "5a27ee9a159ef1d35a1132a306e1202f20b5cd29:html/index.html:generic-api-key:172",
                "1d305fd4f313efabf8b0050d7feb0b5436234278:html/index.html:generic-api-key:172",
                "49b42e15f9b0c70631a0bfb0debcc56dbc1f0c92:html/index.html:generic-api-key:762",
            ],
        )
        for line in lines:
            self.assertRegex(
                line,
                r"^[0-9a-f]{40}:html/index\.html:generic-api-key:[0-9]+$",
            )

    def test_no_temporary_supply_chain_workflows_remain(self) -> None:
        self.assertFalse(
            (ROOT / ".github" / "workflows" / "resolve-supply-chain.yml").exists()
        )
        self.assertFalse(
            (
                ROOT
                / ".github"
                / "workflows"
                / "apply-runtime-data-migration.yml"
            ).exists()
        )
        self.assertFalse((ROOT / "scripts" / "patch-helper-image-ref.py").exists())


if __name__ == "__main__":
    unittest.main()
