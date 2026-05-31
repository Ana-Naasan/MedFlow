import pytest

from backend.app.config import MissingConfigurationError, load_config


def test_load_config_requires_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GOOGLE_GENAI_API_KEY", "OPENFDA_API_KEY", "DEV_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(MissingConfigurationError, match="Missing required environment variables"):
        load_config()


def test_load_config_returns_required_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")

    config = load_config()

    assert config == {
        "GOOGLE_GENAI_API_KEY": "PLACEHOLDER",
        "OPENFDA_API_KEY": "PLACEHOLDER",
        "DEV_TOKEN": "PLACEHOLDER",
    }
