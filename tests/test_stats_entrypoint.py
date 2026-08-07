from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "stats.sh"
GENERATOR = ROOT / "scripts" / "generate-stats.py"
DEPLOY_HELPER = ROOT / "runner" / "release" / "rozkalns-cv-deploy-main"
PRODUCTION_STATS = "/home/andris/docker/cv/html/stats.json"


class StatsEntrypointTests(unittest.TestCase):
    def test_entrypoint_uses_generator_production_default(self) -> None:
        script = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn(
            'ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"',
            script,
        )
        self.assertIn(
            'exec python3 "$ROOT/scripts/generate-stats.py" "$@"',
            script,
        )
        self.assertNotIn('--output "$ROOT/html/stats.json"', script)

    def test_generator_default_targets_the_served_runtime_tree(self) -> None:
        generator = GENERATOR.read_text(encoding="utf-8")
        deploy = DEPLOY_HELPER.read_text(encoding="utf-8")
        self.assertIn(f'"--output", default="{PRODUCTION_STATS}"', generator)
        self.assertIn("RUNTIME='/home/andris/docker/cv'", deploy)
        self.assertIn("--exclude='stats.json'", deploy)

    def test_explicit_output_remains_available_for_safe_validation(self) -> None:
        generator = GENERATOR.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument(\n        "--output", default=', generator)
        self.assertIn("output = Path(args.output)", generator)


if __name__ == "__main__":
    unittest.main()
