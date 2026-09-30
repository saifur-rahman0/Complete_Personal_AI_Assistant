import pytest
from web_research.security import is_safe_url


@pytest.mark.parametrize(
    "forbidden_url,expected_blocked_reason",
    [
        ("file:///C:/Windows/System32/drivers/etc/hosts", "Unsupported scheme"),
        ("ftp://example.com/file.txt", "Unsupported scheme"),
        ("javascript:alert(1)", "Unsupported scheme"),
        ("http://localhost:8000/api", "blocked by SSRF policy"),
        ("http://127.0.0.1:8001/tasks", "blocked by SSRF policy"),
        ("http://10.0.0.1/admin", "blocked by SSRF policy"),
        ("http://192.168.1.1/settings", "blocked by SSRF policy"),
        ("http://172.16.0.10/metrics", "blocked by SSRF policy"),
        ("http://169.254.169.254/latest/meta-data/", "blocked by SSRF policy"),
        ("http://metadata.google.internal/computeMetadata/v1/", "blocked by SSRF policy"),
        ("", "cannot be empty"),
    ],
)
def test_ssrf_blocks_forbidden_urls(forbidden_url, expected_blocked_reason):
    is_safe, reason = is_safe_url(forbidden_url)
    assert not is_safe
    assert expected_blocked_reason.lower() in reason.lower()


def test_ssrf_allows_public_urls():
    safe_urls = [
        "https://en.wikipedia.org/wiki/Main_Page",
        "https://docs.python.org/3/",
    ]
    for url in safe_urls:
        is_safe, reason = is_safe_url(url)
        assert is_safe, f"Expected '{url}' to be safe, got: {reason}"
