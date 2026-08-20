from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"


def _cv_service_block() -> str:
    text = COMPOSE.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^  cv:\n(?P<body>.*?)(?=^  cvbot:\n)", text)
    if match is None:
        raise AssertionError("cv service block not found")
    return match.group(0)


def _cvbot_service_block() -> str:
    text = COMPOSE.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^  cvbot:\n(?P<body>.*?)(?=^networks:\n)", text)
    if match is None:
        raise AssertionError("cvbot service block not found")
    return match.group(0)


class CvContainerHardeningTests(unittest.TestCase):
    def test_cv_rootfs_and_process_boundary_are_hardened(self) -> None:
        block = _cv_service_block()

        self.assertIn("    read_only: true\n", block)
        self.assertIn("    security_opt:\n      - no-new-privileges:true\n", block)
        self.assertIn("    pids_limit: 64\n", block)

    def test_cv_memory_boundary_remains_bounded(self) -> None:
        block = _cv_service_block()

        self.assertIn("    mem_limit: 60m\n", block)
        self.assertIn("    mem_reservation: 30m\n", block)

    def test_cvbot_memory_boundary_remains_bounded(self) -> None:
        block = _cvbot_service_block()

        self.assertIn("    mem_limit: 256m\n", block)

    def test_cv_runtime_writes_are_confined_to_bounded_tmpfs(self) -> None:
        block = _cv_service_block()

        self.assertIn("    tmpfs:\n", block)
        self.assertIn(
            "      - /var/cache/nginx:rw,noexec,nosuid,nodev,size=16m\n", block
        )
        self.assertIn("      - /var/run:rw,noexec,nosuid,nodev,size=1m\n", block)

    def test_cv_ingress_and_content_mounts_remain_restricted(self) -> None:
        block = _cv_service_block()

        self.assertIn("      - 127.0.0.1:8088:80\n", block)
        self.assertIn("      - ./html:/usr/share/nginx/html:ro\n", block)
        self.assertIn(
            "      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro\n", block
        )


if __name__ == "__main__":
    unittest.main()
