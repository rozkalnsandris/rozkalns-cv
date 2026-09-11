import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReducedMotionContractTests(unittest.TestCase):
    def test_source_policy_covers_all_frontend_entries(self) -> None:
        css = (ROOT / "frontend/styles/base.css").read_text(encoding="utf-8")
        media_start = css.index("@media (prefers-reduced-motion: reduce)")
        media_end = css.index("\n}\nbody {", media_start) + 2
        policy = css[media_start:media_end]

        for required in (
            "html { scroll-behavior: auto; }",
            "animation-duration: .01ms !important;",
            "animation-iteration-count: 1 !important;",
            "transition-duration: .01ms !important;",
        ):
            self.assertIn(required, policy)

        for page in ("index.html", "proof.html", "smarthome.html"):
            html = (ROOT / "frontend" / page).read_text(encoding="utf-8")
            self.assertIn('rel="stylesheet" href="./styles/index.css"', html)

    def test_generated_bundle_preserves_reduced_motion_policy(self) -> None:
        manifest = json.loads(
            (ROOT / "frontend-dist-manifest.json").read_text(encoding="utf-8")
        )
        index_css = manifest["index.html"]["css"]
        smarthome_css = manifest["smarthome.html"]["css"]
        self.assertEqual(index_css, smarthome_css)
        self.assertEqual(len(index_css), 1)

        bundle = (ROOT / "html" / index_css[0]).read_text(encoding="utf-8")
        for required in (
            "@media (prefers-reduced-motion:reduce)",
            "html{scroll-behavior:auto}",
            "transition-duration:.01ms!important",
            "animation-duration:.01ms!important",
            "animation-iteration-count:1!important",
        ):
            self.assertIn(required, bundle)


if __name__ == "__main__":
    unittest.main()
