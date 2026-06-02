import pytest

from backend.app.config import MissingConfigurationError, load_config, load_dev_token


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


def test_load_dev_token_requires_only_dev_token(monkeypatch: pytest.MonkeyPatch) -> None:
    # A missing Gemini/openFDA key must NOT block auth — only DEV_TOKEN is required.
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENFDA_API_KEY", raising=False)
    monkeypatch.setenv("DEV_TOKEN", "secret")

    assert load_dev_token() == "secret"


def test_load_dev_token_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_TOKEN", raising=False)

    with pytest.raises(MissingConfigurationError, match="DEV_TOKEN"):
        load_dev_token()
