import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
START_MANIFEST = ROOT / ".github" / "start-github-only.json"
FULL_POLICY = ROOT / ".github" / "source-only-full.json"
AGENTS = ROOT / "AGENTS.md"


class SourceOnlyFullPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.start = json.loads(START_MANIFEST.read_text(encoding="utf-8"))
        cls.policy = json.loads(FULL_POLICY.read_text(encoding="utf-8"))
        cls.agents = AGENTS.read_text(encoding="utf-8")

    def test_default_merge_contract_remains_explicit(self) -> None:
        merge = self.start["merge"]
        self.assertTrue(merge["explicit_owner_authorization"])
        self.assertFalse(merge["auto_merge"])

        conditional = merge["conditional_issue_scoped_full"]
        self.assertEqual(
            conditional["policy_file"],
            ".github/source-only-full.json",
        )
        self.assertFalse(conditional["default_active"])
        self.assertTrue(conditional["owner_activation_required"])
        self.assertTrue(conditional["allows_squash_merge_when_active"])

    def test_activation_is_exact_owner_issue_scoped_command(self) -> None:
        activation = self.policy["activation"]
        self.assertTrue(activation["issue_scoped"])
        self.assertTrue(activation["owner_explicit"])
        self.assertTrue(activation["issue_must_be_open"])
        self.assertFalse(activation["issue_creation_activates"])
        self.assertFalse(activation["issue_body_activates"])
        self.assertFalse(activation["label_activates"])
        self.assertFalse(activation["start_or_continue_activates"])
        self.assertFalse(self.policy["default_active"])

        pattern = re.compile(activation["command_regex"])
        self.assertIsNotNone(
            pattern.fullmatch("AUTO-RUN FULL rozkalns-cv #432")
        )
        for invalid in (
            "AUTO-RUN FULL rozkalns-cv",
            "AUTO-RUN FULL rozkalns-cv #0",
            "AUTO-RUN FULL #432",
            "FULL rozkalns-cv #432",
            "turpini",
            "START rozkalns-cv",
        ):
            self.assertIsNone(pattern.fullmatch(invalid))

        self.assertEqual(
            set(activation["freeze_at_activation"]),
            {
                "issue_number",
                "issue_scope",
                "default_branch",
                "base_sha",
                "policy_revision",
            },
        )

    def test_allowed_mutations_are_finite_source_only_and_disjoint(self) -> None:
        expected_allowed = {
            "branch_create",
            "source_write",
            "content_write",
            "docs_write",
            "tests_write",
            "generated_artifact_refresh",
            "commit_push",
            "draft_pr_create",
            "pr_metadata_update",
            "ready_for_review",
            "scope_preserving_correction",
            "squash_merge",
            "issue_receipt_or_close",
        }
        allowed = set(self.policy["allowed_mutation_classes"])
        forbidden = set(self.policy["forbidden_mutation_classes"])

        self.assertEqual(allowed, expected_allowed)
        self.assertFalse(self.policy["live_authority"])
        self.assertTrue(allowed.isdisjoint(forbidden))

        forbidden_required = {
            "production_deploy",
            "pull_deploy_activation",
            "host_mutation",
            "runtime_mutation",
            "container_runtime_mutation",
            "cloudflare_mutation",
            "dns_mutation",
            "external_account_mutation",
            "openai_account_or_billing_mutation",
            "secret_or_credential_mutation",
            "token_mutation",
            "permission_mutation",
            "repository_settings_mutation",
            "production_data_write",
            "application_data_write",
            "production_rollback_or_cutover",
        }
        self.assertTrue(forbidden_required.issubset(forbidden))

    def test_merge_requires_exact_head_ci_and_review_convergence(self) -> None:
        merge = self.policy["merge"]
        self.assertEqual(merge["method"], "squash")
        self.assertEqual(merge["target_branch"], "main")
        self.assertTrue(merge["bind_expected_head_sha"])
        self.assertTrue(merge["require_current_head_revalidation"])
        self.assertTrue(merge["require_frozen_issue_scope"])
        self.assertTrue(
            merge["require_frozen_base_or_fresh_nonconflicting_revalidation"]
        )
        self.assertTrue(merge["require_exact_head_ci"])
        self.assertTrue(merge["require_zero_unresolved_review_threads"])
        self.assertTrue(merge["require_no_actionable_reviews"])

    def test_drift_error_and_ambiguity_fail_closed(self) -> None:
        fail_closed = self.policy["fail_closed"]
        conditions = set(fail_closed["conditions"])
        self.assertTrue(
            {
                "scope_expansion",
                "branch_or_head_drift",
                "unexpected_failure",
                "tool_error_or_timeout",
                "authorization_ambiguity",
                "privacy_or_publication_uncertainty",
                "merge_condition_mismatch",
            }.issubset(conditions)
        )
        self.assertFalse(fail_closed["automatic_retry_after_mutation_error"])
        self.assertFalse(fail_closed["automatic_rollback"])
        self.assertFalse(fail_closed["automatic_cleanup"])
        self.assertFalse(fail_closed["alternate_mutation_path"])

        corrections = self.policy["corrections"]
        self.assertTrue(corrections["scope_preserving_only"])
        self.assertEqual(corrections["maximum"], 2)

    def test_publication_boundary_is_explicit(self) -> None:
        privacy = self.policy["privacy"]
        self.assertTrue(privacy["repository_is_public"])
        forbidden = set(privacy["forbidden_publication_classes"])
        self.assertTrue(
            {
                "private_job_search_notes",
                "private_vacancy_or_company_details",
                "residential_or_street_address",
                "protected_phone",
                "credentials",
                "secrets",
                "tokens",
            }.issubset(forbidden)
        )

    def test_agents_documents_activation_and_live_exclusion(self) -> None:
        self.assertIn(
            "## Repository-local source-only FULL mode",
            self.agents,
        )
        self.assertIn(
            "AUTO-RUN FULL rozkalns-cv #<issue>",
            self.agents,
        )
        self.assertIn(
            ".github/source-only-full.json",
            self.agents,
        )
        self.assertIn(
            "does not grant LIVE authority",
            self.agents,
        )


if __name__ == "__main__":
    unittest.main()
