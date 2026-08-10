from __future__ import annotations

import importlib.util
from pathlib import Path
import shlex
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-input-id.py"
SPEC = importlib.util.spec_from_file_location("build_input_id", SCRIPT)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import bootstrap
    raise RuntimeError("could not load build-input-id.py")
BUILD_INPUT_ID = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_INPUT_ID)


def dockerfile_copy_inputs() -> set[str]:
    dockerfile = (ROOT / "bot" / "Dockerfile").read_text(encoding="utf-8")
    logical_lines: list[str] = []
    current = ""

    for raw in dockerfile.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current = f"{current} {stripped}".strip()
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        logical_lines.append(current)
        current = ""

    if current:
        raise AssertionError("unterminated Dockerfile continuation")

    inputs: set[str] = set()
    for line in logical_lines:
        tokens = shlex.split(line, posix=True)
        if not tokens or tokens[0].upper() != "COPY":
            continue
        args = tokens[1:]
        while args and args[0].startswith("--"):
            args.pop(0)
        if len(args) < 2:
            raise AssertionError(f"unsupported Dockerfile COPY: {line}")
        sources = args[:-1]
        for source in sources:
            if any(character in source for character in "*?["):
                raise AssertionError(
                    f"wildcard Dockerfile COPY needs explicit identity handling: {source}"
                )
            inputs.add(f"bot/{source.lstrip('./')}")
    return inputs


class BuildInputIdentityTests(unittest.TestCase):
    def test_identity_covers_exact_docker_copy_source_contract(self) -> None:
        self.assertEqual(
            set(BUILD_INPUT_ID.CVBOT_DOCKER_COPY_INPUTS),
            dockerfile_copy_inputs(),
        )

    def test_every_declared_input_exists_and_rows_are_deterministic(self) -> None:
        digest, rows = BUILD_INPUT_ID.calculate(ROOT)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(
            [relative for relative, _ in rows],
            list(BUILD_INPUT_ID.INPUTS),
        )
        for relative, file_digest in rows:
            self.assertTrue((ROOT / relative).is_file(), relative)
            self.assertRegex(file_digest, r"^[0-9a-f]{64}$")

    def test_every_docker_copy_source_changes_build_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in BUILD_INPUT_ID.INPUTS:
                source = ROOT / relative
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)

            baseline, _ = BUILD_INPUT_ID.calculate(root)
            for relative in BUILD_INPUT_ID.CVBOT_DOCKER_COPY_INPUTS:
                path = root / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n# build-input-identity-regression\n")
                changed, _ = BUILD_INPUT_ID.calculate(root)
                self.assertNotEqual(baseline, changed, relative)
                path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
