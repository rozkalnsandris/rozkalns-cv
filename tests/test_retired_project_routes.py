from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RetiredProjectRoutesTests(unittest.TestCase):
    def test_retired_learning_project_is_not_publicly_advertised(self) -> None:
        profile = json.loads((ROOT / "content/profile.json").read_text(encoding="utf-8"))
        self.assertNotIn("linux-ops-lab", {p["id"] for p in profile["projects"]})
        self.assertNotIn("linux-operations-lab-learning", {p["id"] for p in profile["education"]})
        evidence = json.loads((ROOT / "content/evidence.json").read_text(encoding="utf-8"))
        self.assertNotIn("linux-operations-lab-readme", evidence["evidence"])
        manifest = json.loads((ROOT / "frontend-dist-manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(any("/lab/" in row["path"] for row in manifest["_localized"].values()))
        self.assertNotIn("/lab/", (ROOT / "html/sitemap.xml").read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "frontend/lab.html").exists())
        self.assertFalse((ROOT / "content/lab.json").exists())
        for language in ("en", "de", "lv"):
            self.assertFalse((ROOT / "html" / language / "lab" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
