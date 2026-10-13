from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SIMPLE_NGINX = ROOT / "deploy/simple-deploy/nginx.conf"
LEGACY_NGINX = ROOT / "nginx.conf"
GENERATOR = ROOT / "scripts/generate-stats.py"


class SimpleDeployLiveStatsTests(unittest.TestCase):
    def test_only_exact_public_stats_file_is_aliased_from_read_only_mount(self) -> None:
        conf = SIMPLE_NGINX.read_text(encoding="utf-8")
        match = re.search(r"location = /stats\.json \{([^{}]*)\}", conf)
        self.assertIsNotNone(match)
        route = match.group(1)
        self.assertIn("alias /srv/cv/host-stats/stats.json;", route)
        self.assertIn("default_type application/json;", route)
        self.assertIn('add_header Cache-Control "no-store" always;', route)
        self.assertNotIn("try_files", route)
        self.assertNotIn("proxy_pass", route)
        self.assertIn("root /srv/cv/html;", conf)
        self.assertEqual(conf.count("alias /srv/cv/host-stats"), 1)
        self.assertNotIn("location /host-stats", conf)
        self.assertNotIn("root /srv/cv/host-stats;", conf)

    def test_host_snapshot_replacement_requires_a_directory_bind(self) -> None:
        generator = GENERATOR.read_text(encoding="utf-8")
        self.assertIn("os.replace(temporary, output)", generator)
        self.assertIn("dir=output.parent", generator)
        self.assertIn('"/home/andris/docker/cv/html/stats.json"', generator)

    def test_legacy_two_container_stats_route_is_unchanged(self) -> None:
        old = LEGACY_NGINX.read_text(encoding="utf-8")
        self.assertIn("location = /stats.json {", old)
        self.assertIn("try_files $uri =404;", old)
        self.assertNotIn("/srv/cv/host-stats", old)


if __name__ == "__main__":
    unittest.main()
