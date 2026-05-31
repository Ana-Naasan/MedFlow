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
