from __future__ import annotations

import os

REQUIRED_ENV_VARS = ("GOOGLE_GENAI_API_KEY", "OPENFDA_API_KEY", "DEV_TOKEN")

# How long a cached resource stays fresh before a re-fetch is triggered.
CACHE_TTL_SECONDS: int = int(os.environ.get("CACHE_TTL_SECONDS", "300"))


class MissingConfigurationError(RuntimeError):
    """Raised when a required runtime secret or key is not set."""


def load_config() -> dict[str, str]:
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        joined = ", ".join(missing)
        raise MissingConfigurationError(f"Missing required environment variables: {joined}")

    return {name: os.environ[name] for name in REQUIRED_ENV_VARS}


def load_dev_token() -> str:
    """Return the dev auth token, validating ONLY ``DEV_TOKEN``.

    Decoupled from :func:`load_config` so that a missing ``GOOGLE_GENAI_API_KEY``
    or ``OPENFDA_API_KEY`` — used only on the reasoning path, which degrades
    gracefully — does not 500 every authenticated request.
    """
    token = os.environ.get("DEV_TOKEN")
    if not token:
        raise MissingConfigurationError("Missing required environment variable: DEV_TOKEN")
    return token
