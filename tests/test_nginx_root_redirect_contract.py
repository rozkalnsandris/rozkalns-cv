from pathlib import Path


NGINX = Path("nginx.conf")


def _root_location_block() -> str:
    source = NGINX.read_text(encoding="utf-8")
    start = source.index("    location = / {")
    end = source.index("\n    }", start) + len("\n    }")
    return source[start:end]


def test_public_root_redirect_forces_canonical_https() -> None:
    block = _root_location_block()

    host_guard = "if ($host = rozkalns.net) {"
    canonical = "return 308 https://rozkalns.net/en/$is_args$args;"
    local_fallback = "return 308 /en/$is_args$args;"

    assert host_guard in block
    assert canonical in block
    assert local_fallback in block
    assert block.index(host_guard) < block.index(canonical) < block.index(local_fallback)
