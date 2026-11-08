from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_codeql_evidence.py"
SPEC = importlib.util.spec_from_file_location("check_codeql_evidence", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

EvidenceError = MODULE.EvidenceError
evaluate_check_runs = MODULE.evaluate_check_runs
fetch_check_runs = MODULE.fetch_check_runs


def check(name: str, status: str = "completed", conclusion="success", app="github-actions"):
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "app": {"slug": app},
    }


def success_payload():
    return {
        "check_runs": [
            check("Analyze (actions)"),
            check("Analyze (python)"),
            check("Analyze (javascript-typescript)"),
            check("CodeQL", app="github-advanced-security"),
        ]
    }


def dependabot_fallback_payload():
    return {
        "check_runs": [
            check("CodeQL", conclusion="neutral", app="github-advanced-security"),
            check("Dependabot CodeQL (actions)"),
            check("Dependabot CodeQL (python)"),
            check("Dependabot CodeQL (javascript-typescript)"),
        ]
    }


class CodeQLEvidenceEvaluationTests(unittest.TestCase):
    def test_complete_success_requires_all_four_checks(self) -> None:
        complete, pending = evaluate_check_runs(success_payload())
        self.assertTrue(complete)
        self.assertEqual(pending, ())

    def test_missing_check_waits_fail_closed(self) -> None:
        payload = success_payload()
        payload["check_runs"] = payload["check_runs"][:-1]
        complete, pending = evaluate_check_runs(payload)
        self.assertFalse(complete)
        self.assertEqual(pending, ("missing:CodeQL",))

    def test_in_progress_check_waits_fail_closed(self) -> None:
        payload = success_payload()
        payload["check_runs"][1] = check(
            "Analyze (python)", status="in_progress", conclusion=None
        )
        complete, pending = evaluate_check_runs(payload)
        self.assertFalse(complete)
        self.assertEqual(pending, ("pending:Analyze (python):in_progress",))

    def test_transient_neutral_meta_check_waits_without_fallback(self) -> None:
        payload = success_payload()
        payload["check_runs"][-1] = check(
            "CodeQL", conclusion="neutral", app="github-advanced-security"
        )
        complete, pending = evaluate_check_runs(payload)
        self.assertFalse(complete)
        self.assertEqual(
            pending,
            (
                "pending:CodeQL:neutral",
                "missing:Dependabot CodeQL (actions)",
                "missing:Dependabot CodeQL (python)",
                "missing:Dependabot CodeQL (javascript-typescript)",
            ),
        )

    def test_neutral_meta_accepts_complete_dependabot_same_head_fallback(self) -> None:
        complete, pending = evaluate_check_runs(dependabot_fallback_payload())
        self.assertTrue(complete)
        self.assertEqual(pending, ())

    def test_dependabot_fallback_failure_fails_closed(self) -> None:
        payload = dependabot_fallback_payload()
        payload["check_runs"][1] = check(
            "Dependabot CodeQL (actions)", conclusion="failure"
        )
        with self.assertRaises(EvidenceError):
            evaluate_check_runs(payload)

    def test_dependabot_fallback_requires_github_actions_provenance(self) -> None:
        payload = dependabot_fallback_payload()
        payload["check_runs"][1] = check(
            "Dependabot CodeQL (actions)", app="third-party"
        )
        with self.assertRaises(EvidenceError):
            evaluate_check_runs(payload)

    def test_neutral_meta_requires_github_advanced_security_provenance(self) -> None:
        payload = dependabot_fallback_payload()
        payload["check_runs"][0] = check(
            "CodeQL", conclusion="neutral", app="third-party"
        )
        with self.assertRaises(EvidenceError):
            evaluate_check_runs(payload)

    def test_failed_meta_check_fails_closed(self) -> None:
        payload = success_payload()
        payload["check_runs"][-1] = check(
            "CodeQL", conclusion="failure", app="github-advanced-security"
        )
        with self.assertRaises(EvidenceError):
            evaluate_check_runs(payload)

    def test_duplicate_required_check_fails_closed(self) -> None:
        payload = success_payload()
        payload["check_runs"].append(check("Analyze (python)"))
        with self.assertRaises(EvidenceError):
            evaluate_check_runs(payload)

    def test_non_success_analyzer_terminal_states_fail_closed(self) -> None:
        for conclusion in ("failure", "neutral", "cancelled", "timed_out", "skipped"):
            with self.subTest(conclusion=conclusion):
                payload = success_payload()
                payload["check_runs"][0] = check(
                    "Analyze (actions)", conclusion=conclusion
                )
                with self.assertRaises(EvidenceError):
                    evaluate_check_runs(payload)

    def test_malformed_payload_fails_closed(self) -> None:
        for payload in (None, [], {}, {"check_runs": {}}, {"check_runs": [None]}):
            with self.subTest(payload=payload):
                with self.assertRaises(EvidenceError):
                    evaluate_check_runs(payload)

    def test_unknown_status_fails_closed(self) -> None:
        payload = success_payload()
        payload["check_runs"][0] = check(
            "Analyze (actions)", status="mystery", conclusion=None
        )
        with self.assertRaises(EvidenceError):
            evaluate_check_runs(payload)


class FakeResponse:
    def __init__(self, payload) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class CodeQLEvidenceFetchTests(unittest.TestCase):
    @patch.object(MODULE, "urlopen")
    def test_fetch_uses_exact_sha_latest_filter_and_never_puts_token_in_url(
        self, mocked_urlopen
    ) -> None:
        mocked_urlopen.return_value = FakeResponse(success_payload())
        token = "synthetic-test-token"
        sha = "a" * 40

        payload = fetch_check_runs("owner/repo", sha, token)

        self.assertEqual(payload, success_payload())
        request = mocked_urlopen.call_args.args[0]
        self.assertIn(f"/commits/{sha}/check-runs", request.full_url)
        self.assertIn("per_page=100", request.full_url)
        self.assertIn("filter=latest", request.full_url)
        self.assertNotIn(token, request.full_url)
        self.assertEqual(request.get_header("Authorization"), f"Bearer {token}")

    def test_invalid_repository_sha_or_empty_token_fails_before_network(self) -> None:
        cases = (
            ("owner", "a" * 40, "token"),
            ("owner/repo", "A" * 40, "token"),
            ("owner/repo", "a" * 39, "token"),
            ("owner/repo", "a" * 40, ""),
        )
        for repository, sha, token in cases:
            with self.subTest(repository=repository, sha=sha, token=bool(token)):
                with self.assertRaises(EvidenceError):
                    fetch_check_runs(repository, sha, token)


class CodeQLEvidenceWorkflowContractTests(unittest.TestCase):
    def test_dependabot_fallback_is_exact_head_read_only_and_immutably_pinned(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "codeql-evidence.yml").read_text(
            encoding="utf-8"
        )
        pin = "33d7b85da1a04171e211befe2c739303b9a4c066"
        self.assertIn("github.event.pull_request.user.login == 'dependabot[bot]'", workflow)
        self.assertIn(
            "startsWith(github.event.pull_request.head.ref, 'dependabot/github_actions/')",
            workflow,
        )
        self.assertIn(f"github/codeql-action/init@{pin}", workflow)
        self.assertIn(f"github/codeql-action/analyze@{pin}", workflow)
        self.assertIn("upload: never", workflow)
        self.assertIn("needs:\n      - dependabot-codeql-fallback", workflow)
        self.assertIn("if: ${{ always() }}", workflow)
        self.assertNotIn("security-events: write", workflow)
        self.assertNotIn("pull_request_target:", workflow)


if __name__ == "__main__":
    unittest.main()
