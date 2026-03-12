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
