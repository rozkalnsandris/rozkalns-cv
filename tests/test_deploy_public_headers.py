from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-main.yml"


class DeployPublicHeaderTests(unittest.TestCase):
    def test_deploy_verifier_uses_portable_case_insensitive_header_parsing(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("IGNORECASE=1", text)
        self.assertIn('tolower($1) == "content-type:"', text)
        self.assertIn('tolower($1) == "content-security-policy:"', text)

    def test_posix_awk_programs_parse_cloudflare_lowercase_headers(self) -> None:
        headers = (
            "HTTP/2 200 \r\n"
            "content-type: text/javascript\r\n"
            "cache-control: public, max-age=31536000, immutable\r\n"
            "content-security-policy: default-src 'self'; script-src-attr 'none';\r\n"
            "x-content-type-options: nosniff\r\n"
        )
        content_type = subprocess.run(
            [
                "awk",
                'tolower($1) == "content-type:" { value=$2; sub(/\\r$/, "", value); print value; exit }',
            ],
            input=headers,
            text=True,
            check=True,
            capture_output=True,
        ).stdout.strip()
        csp = subprocess.run(
            [
                "awk",
                'tolower($1) == "content-security-policy:" { sub(/\\r$/, ""); sub(/^[^:]+:[[:space:]]*/, ""); print; exit }',
            ],
            input=headers,
            text=True,
            check=True,
            capture_output=True,
        ).stdout.strip()

        self.assertEqual(content_type, "text/javascript")
        self.assertEqual(csp, "default-src 'self'; script-src-attr 'none';")


if __name__ == "__main__":
    unittest.main()
