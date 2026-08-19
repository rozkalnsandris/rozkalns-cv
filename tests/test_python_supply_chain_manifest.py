from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "bot" / "requirements.txt"
SUPPLY = ROOT / "security" / "supply-chain.json"


def normalize_package_name(name: str) -> str:
    return name.lower().replace("_", "-")


class PythonSupplyChainManifestContractTests(unittest.TestCase):
    def test_python_audit_snapshot_matches_hash_lock(self) -> None:
        lock_text = LOCK.read_text(encoding="utf-8")
        rows = re.findall(
            r"(?m)^([a-z0-9][a-z0-9_.-]*)==([^\\\s]+)",
            lock_text,
        )
        self.assertGreaterEqual(len(rows), 10)

        locked: dict[str, str] = {}
        for raw_name, version in rows:
            name = normalize_package_name(raw_name)
            self.assertNotIn(name, locked, f"duplicate locked package: {name}")
            locked[name] = version

        manifest = json.loads(SUPPLY.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("schema_version"), 1)
        snapshot = manifest.get("python_packages")
        self.assertIsInstance(snapshot, dict)
        assert isinstance(snapshot, dict)

        self.assertEqual(set(snapshot), set(locked))
        for name, version in locked.items():
            record = snapshot[name]
            self.assertIsInstance(record, dict)
            assert isinstance(record, dict)
            self.assertEqual(record.get("version"), version)

            release_url = record.get("release_url")
            self.assertIsInstance(release_url, str)
            assert isinstance(release_url, str)
            self.assertRegex(
                release_url,
                rf"^https://pypi\.org/project/[^/]+/{re.escape(version)}/$",
            )

            serial = record.get("pypi_last_serial")
            self.assertIsInstance(serial, int)
            assert isinstance(serial, int)
            self.assertGreater(serial, 0)


if __name__ == "__main__":
    unittest.main()
