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

    def test_duplicate_required_check_fails_closed(self) -> None:
        payload = success_payload()
        payload["check_runs"].append(check("Analyze (python)"))
        with self.assertRaises(EvidenceError):
            evaluate_check_runs(payload)

    def test_non_success_terminal_states_fail_closed(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
