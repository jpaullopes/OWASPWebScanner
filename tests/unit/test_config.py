import owasp_scanner.core.config as config_module  # type: ignore[import]

from tests.helpers.owasp_imports import load_configuration


def test_load_configuration_uses_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "load_dotenv", lambda *_args, **_kwargs: False)
    report_path = tmp_path / "relatorio.json"

    monkeypatch.setenv("SESSION_COOKIE", "session=value")
    monkeypatch.setenv("EMAIL_LOGIN", "user@example.com")
    monkeypatch.setenv("PASSWORD_LOGIN", "secret")
    monkeypatch.setenv("HEADLESS", "true")

    config = load_configuration("https://example.com/", str(report_path))

    assert config.target_url == "https://example.com"
    assert config.session_cookie == "session=value"
    assert config.auth_email == "user@example.com"
    assert config.auth_password == "secret"
    assert config.headless is True
    assert config.report_path == report_path.resolve()


def test_load_configuration_defaults(monkeypatch):
    monkeypatch.setattr(config_module, "load_dotenv", lambda *_args, **_kwargs: False)
    for key in ["SESSION_COOKIE", "EMAIL_LOGIN", "PASSWORD_LOGIN", "HEADLESS"]:
        monkeypatch.delenv(key, raising=False)

    config = load_configuration("https://example.com/base//")

    assert config.target_url == "https://example.com/base"
    assert config.session_cookie is None
    assert config.auth_email is None
    assert config.auth_password is None
    assert config.headless is False
