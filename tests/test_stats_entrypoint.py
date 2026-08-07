from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "stats.sh"


class StatsEntrypointTests(unittest.TestCase):
    def test_default_output_tracks_active_checkout(self) -> None:
        script = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn('ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"', script)
        self.assertIn('set -- --output "$ROOT/html/stats.json" "$@"', script)
        self.assertNotIn("/home/andris/docker/cv/html/stats.json", script)

    def test_explicit_output_is_preserved_for_validation(self) -> None:
        script = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn('arg" == "--output"', script)
        self.assertIn('arg" == --output=*', script)
        self.assertIn('if [[ "$has_output" == false ]]', script)


if __name__ == "__main__":
    unittest.main()
