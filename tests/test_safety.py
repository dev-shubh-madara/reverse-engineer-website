import pytest

from sitere import safety


def test_rejects_non_http():
    with pytest.raises(safety.Refused):
        safety.validate_target("ftp://example.com")


def test_rejects_embedded_credentials():
    with pytest.raises(safety.Refused):
        safety.validate_target("https://user:pass@example.com")


def test_blocks_private_host(monkeypatch):
    monkeypatch.delenv("SITERE_ALLOW_LOCAL", raising=False)
    with pytest.raises(safety.Refused):
        safety.validate_target("http://127.0.0.1:8000")


def test_allows_loopback_only_for_preview():
    parsed = safety.validate_target("http://localhost:5000", allow_loopback=True)
    assert parsed.hostname == "localhost"


def test_redacts_known_secret_shapes():
    assert "[REDACTED]" in safety.redact_text("key ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345")
    assert "[REDACTED]" in safety.redact_text("stripe sk_live_abcdefghij1234567890")
    assert safety.redact_text("just normal text") == "just normal text"
