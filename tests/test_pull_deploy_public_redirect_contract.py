from pathlib import Path


DEPLOY_HELPER = Path("runner/release/rozkalns-cv-pull-deploy-main")


def _public_contract_function() -> str:
    source = DEPLOY_HELPER.read_text(encoding="utf-8")
    start = source.index("verify_public_frontend_contracts() {")
    end = source.index("\n}\n\ninstall -d -m 0700", start) + 2
    return source[start:end]


def test_rollout_verifier_matches_intentional_root_redirect_policy() -> None:
    contract = _public_contract_function()

    assert 'expected_location="${PUBLIC_URL%/}/en/"' in contract
    assert "--write-out '%{http_code}'" in contract
    assert '[[ "$root_status" != 308 ]]' in contract
    assert '[[ "$root_location" != "$expected_location" ]]' in contract
    assert '--output "$html" \\\n        "$expected_location"' in contract
    assert '--output "$html" \\\n        "$PUBLIC_URL"' not in contract


def test_rollout_verifier_checks_page_headers_after_redirect() -> None:
    contract = _public_contract_function()

    assert 'page_headers="$tmp/en.headers"' in contract
    assert '--dump-header "$page_headers"' in contract
    assert '"$page_headers"\n    )"' in contract
    assert 'PUBLIC_ROOT_REDIRECT=PASS location=%s' in contract
    assert 'PUBLIC_SITE=PASS' in contract
