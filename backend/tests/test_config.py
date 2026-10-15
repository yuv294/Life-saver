"""Production-safety checks on configuration defaults."""

from config import Settings


def make(**kw):
    return Settings(_env_file=None, **kw)


def test_default_secrets_are_flagged():
    weak = make().insecure_defaults()
    assert "SECRET_KEY" in weak and "INTERNAL_API_SECRET" in weak


def test_real_secrets_pass():
    assert make(secret_key="x" * 40, internal_api_secret="y" * 40).insecure_defaults() == []


def test_dev_auth_bypass_is_flagged():
    weak = make(secret_key="x" * 40, internal_api_secret="y" * 40, dev_auth_bypass=True).insecure_defaults()
    assert len(weak) == 1 and weak[0].startswith("DEV_AUTH_BYPASS")
