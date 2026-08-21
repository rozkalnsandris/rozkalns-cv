from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PULL_HELPER = ROOT / "runner" / "release" / "rozkalns-cv-pull-deploy-main"


class PullDeployValidationTmpCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pull = PULL_HELPER.read_text(encoding="utf-8")
        subprocess.run(["bash", "-n", str(PULL_HELPER)], check=True)

    def test_validation_tmp_capacity_is_pinned_and_fail_closed(self) -> None:
        for marker in (
            "VALIDATION_TMP_ROOT='/tmp'",
            "MIN_VALIDATION_TMP_BYTES=268435456",
            "MIN_VALIDATION_TMP_INODES=10000",
            '"$VALIDATION_TMP_ROOT" "$MIN_VALIDATION_TMP_BYTES" "$MIN_VALIDATION_TMP_INODES"',
            "validation temp filesystem lacks required free space or inodes",
        ):
            self.assertIn(marker, self.pull)

    def test_validation_tmp_gate_precedes_source_validation_and_mutation(self) -> None:
        temp_gate = self.pull.index(
            'require_capacity \\\n    "$VALIDATION_TMP_ROOT"'
        )
        source_validation = self.pull.index(
            'export TMPDIR="$1"; cd "$2" && exec bash '
            '"$2/scripts/validate-source.sh" "$2"'
        )
        candidate = self.pull.index(
            "prepare_candidate || fail 'candidate preparation failed'"
        )
        backup = self.pull.index(
            'BACKUP="$BACKUP_ROOT/${STAMP}-${OLD_SHA:-unknown}"'
        )
        mutation = self.pull.index("MUTATION_STARTED=true")

        self.assertLess(temp_gate, source_validation)
        self.assertLess(source_validation, candidate)
        self.assertLess(candidate, backup)
        self.assertLess(backup, mutation)

    def test_source_validation_uses_the_capacity_checked_tmp_root(self) -> None:
        for marker in (
            'export TMPDIR="$1"',
            'bash "$VALIDATION_TMP_ROOT" "$STAGE"',
            '"$2/scripts/validate-source.sh" "$2"',
        ):
            self.assertIn(marker, self.pull)


if __name__ == "__main__":
    unittest.main()
