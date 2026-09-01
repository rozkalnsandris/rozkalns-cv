from pathlib import Path


DEPLOY_HELPER = Path("runner/release/rozkalns-cv-pull-deploy-main")


def _deploy_helper_source() -> str:
    return DEPLOY_HELPER.read_text(encoding="utf-8")


def _public_contract_function() -> str:
    source = _deploy_helper_source()
    start = source.index("verify_public_frontend_contracts() {")
    end = source.index("\n}\n\ninstall -d -m 0700", start) + 2
    return source[start:end]


def test_rollout_verifier_matches_intentional_root_redirect_policy() -> None:
    contract = _public_contract_function()

    assert 'expected_location="${PUBLIC_URL%/}/en/"' in contract
    assert "--write-out '%{http_code}'" in contract
    assert (
        '[[ "$root_status" == 308 && "$root_location" == "$expected_location" ]]'
        in contract
    )
    assert (
        '[[ "$root_status" != 308 || "$root_location" != "$expected_location" ]]'
        in contract
    )
    assert '--output "$html" \\\n        "$expected_location"' in contract
    assert '--output "$html" \\\n        "$PUBLIC_URL"' not in contract


def test_rollout_verifier_separates_local_origin_from_public_ingress() -> None:
    contract = _public_contract_function()

    assert 'expected_local_location="${LOCAL_URL%/}/en/"' in contract
    assert '"$LOCAL_URL"' in contract
    assert '[[ "$local_root_status" != 308 ]]' in contract
    assert 'LOCAL_ROOT_REDIRECT=FAIL reason=status' in contract
    assert 'LOCAL_ROOT_REDIRECT=FAIL reason=location' in contract
    assert 'LOCAL_ROOT_REDIRECT=PASS status=%s location=%s' in contract


def test_rollout_verifier_retries_public_root_without_weakening_contract() -> None:
    source = _deploy_helper_source()
    contract = _public_contract_function()

    assert "PUBLIC_CONTRACT_ATTEMPTS=6" in source
    assert "PUBLIC_CONTRACT_RETRY_DELAY_SECONDS=5" in source
    assert (
        "for (( attempt = 1; attempt <= PUBLIC_CONTRACT_ATTEMPTS; attempt++ )); do"
        in contract
    )
    assert "--header 'Cache-Control: no-cache'" in contract
    assert "--header 'Pragma: no-cache'" in contract
    assert 'PUBLIC_ROOT_REDIRECT_ATTEMPT=RETRY' in contract
    assert 'sleep "$PUBLIC_CONTRACT_RETRY_DELAY_SECONDS"' in contract
    assert 'PUBLIC_ROOT_REDIRECT=FAIL status=%s location=%s' in contract
    assert 'PUBLIC_ROOT_REDIRECT=PASS location=%s' in contract


def test_rollout_verifier_emits_stage_specific_failure_evidence() -> None:
    contract = _public_contract_function()

    assert 'PUBLIC_SITE=FAIL reason=page-fetch' in contract
    assert 'PUBLIC_SITE=FAIL reason=module-path-missing' in contract
    assert 'PUBLIC_MODULE_MIME=FAIL reason=module-fetch' in contract
    assert 'PUBLIC_MODULE_MIME=FAIL actual=%s' in contract
    assert 'PUBLIC_CACHE_IMMUTABLE=FAIL path=%s' in contract
    assert 'PUBLIC_NOSNIFF=FAIL path=%s' in contract
    assert 'PUBLIC_CSP_NONCE=FAIL reason=policy-contract' in contract


def test_rollout_verifier_checks_page_headers_after_redirect() -> None:
    contract = _public_contract_function()

    assert 'page_headers="$tmp/en.headers"' in contract
    assert '--dump-header "$page_headers"' in contract
    assert '"$page_headers"\n    )"' in contract
    assert 'PUBLIC_SITE=PASS' in contract
