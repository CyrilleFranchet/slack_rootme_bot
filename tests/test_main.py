import pytest

from config import Settings


def test_settings_requires_missing_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in (
        "SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET",
        "SLACK_APP_TOKEN",
        "ROOTME_API_KEY",
    ):
        monkeypatch.delenv(env_var, raising=False)

    with pytest.raises(ValueError, match="SLACK_BOT_TOKEN"):
        Settings.from_env()


def test_settings_loads_rootme_api_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "secret")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-test")
    monkeypatch.setenv("ROOTME_API_KEY", "api-key")
    monkeypatch.delenv("ROOTME_API_BASE_URL", raising=False)
    monkeypatch.delenv("ROOTME_TIMEOUT_SECONDS", raising=False)

    settings = Settings.from_env()

    assert settings.rootme_api_base_url == "https://api.www.root-me.org"
    assert settings.rootme_timeout_seconds == 10.0
    assert settings.ranking_refresh_interval_seconds == 3600
