from types import SimpleNamespace

from app import auth_routes_multitenant as auth_routes


def _request(hostname: str, host_header: str | None = None):
    return SimpleNamespace(
        url=SimpleNamespace(hostname=hostname),
        headers={"host": host_header or hostname},
    )


def test_email_verification_bypasses_local_signup_when_not_strict_env(monkeypatch):
    monkeypatch.setattr(auth_routes, "EMAIL_VERIFICATION_REQUIRED", True)
    monkeypatch.setenv("ENVIRONMENT", "development")

    required = auth_routes._email_verification_required_for_request(_request("127.0.0.1"))

    assert required is False


def test_email_verification_bypasses_local_signup_even_if_env_name_is_strict(monkeypatch):
    monkeypatch.setattr(auth_routes, "EMAIL_VERIFICATION_REQUIRED", True)
    monkeypatch.setenv("ENVIRONMENT", "production")

    required = auth_routes._email_verification_required_for_request(_request("127.0.0.1"))

    assert required is False


def test_email_verification_stays_required_in_production_for_external_host(monkeypatch):
    monkeypatch.setattr(auth_routes, "EMAIL_VERIFICATION_REQUIRED", True)
    monkeypatch.setenv("ENVIRONMENT", "production")

    required = auth_routes._email_verification_required_for_request(_request("mlprohub.com.br"))

    assert required is True


def test_email_verification_stays_required_for_external_host(monkeypatch):
    monkeypatch.setattr(auth_routes, "EMAIL_VERIFICATION_REQUIRED", True)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    required = auth_routes._email_verification_required_for_request(_request("mlprohub.com.br"))

    assert required is True


def test_email_verification_can_be_disabled_by_config(monkeypatch):
    monkeypatch.setattr(auth_routes, "EMAIL_VERIFICATION_REQUIRED", False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    required = auth_routes._email_verification_required_for_request(_request("mlprohub.com.br"))

    assert required is False
