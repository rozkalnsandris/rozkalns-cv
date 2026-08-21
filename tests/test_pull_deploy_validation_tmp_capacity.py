from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PULL_HELPER = ROOT / "runner" / "release" / "rozkalns-cv-pull-deploy-main"
VALIDATOR = ROOT / "scripts" / "validate-source.sh"


class PullDeployValidationTmpCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pull = PULL_HELPER.read_text(encoding="utf-8")
        cls.validator = VALIDATOR.read_text(encoding="utf-8")
        subprocess.run(["bash", "-n", str(PULL_HELPER)], check=True)
        subprocess.run(["bash", "-n", str(VALIDATOR)], check=True)

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
            '"$VALIDATION_TMP_ROOT" "$MIN_VALIDATION_TMP_BYTES"'
        )
        tmp_export = self.pull.index('export TMPDIR="$VALIDATION_TMP_ROOT"')
        source_validation = self.pull.index(
            "'cd \"$1\" && exec bash \"$1/scripts/validate-source.sh\" \"$1\"'"
        )
        candidate = self.pull.index(
            "prepare_candidate || fail 'candidate preparation failed'"
        )
        backup = self.pull.index(
            'BACKUP="$BACKUP_ROOT/${STAMP}-${OLD_SHA:-unknown}"'
        )
        mutation = self.pull.index("MUTATION_STARTED=true")

        self.assertLess(temp_gate, tmp_export)
        self.assertLess(tmp_export, source_validation)
        self.assertLess(source_validation, candidate)
        self.assertLess(candidate, backup)
        self.assertLess(backup, mutation)

    def test_source_validation_uses_the_capacity_checked_tmp_root(self) -> None:
        for marker in (
            'export TMPDIR="$VALIDATION_TMP_ROOT"',
            'bash "$STAGE"',
            'unset TMPDIR',
        ):
            self.assertIn(marker, self.pull)

        self.assertIn(
            'mktemp -d "${TMPDIR:-/tmp}/rozkalns-cv-validate.XXXXXXXX"',
            self.validator,
        )

        tmp_export = self.pull.index('export TMPDIR="$VALIDATION_TMP_ROOT"')
        runuser = self.pull.index('runuser -u "$OWNER" -- bash -c', tmp_export)
        tmp_unset = self.pull.index("unset TMPDIR", runuser)
        self.assertLess(tmp_export, runuser)
        self.assertLess(runuser, tmp_unset)


if __name__ == "__main__":
    unittest.main()
