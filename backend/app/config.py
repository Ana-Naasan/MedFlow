from __future__ import annotations

import os

REQUIRED_ENV_VARS = ("GOOGLE_GENAI_API_KEY", "OPENFDA_API_KEY", "DEV_TOKEN")

# How long a cached resource stays fresh before a re-fetch is triggered.
CACHE_TTL_SECONDS: int = int(os.environ.get("CACHE_TTL_SECONDS", "300"))

# Upper bound on the live Gemini reasoning call that runs inside the /packet
# request path. A slow or hung call must not block the page until it gives up
# ("Failed to load packet", #90) — once this is exceeded the pipeline abstains
# to the citation-safe static scaffold. Pre-warming the cache (#34) keeps the
# demo's first load a sub-second HIT; this bound protects the cold/miss path.
REASONING_TIMEOUT_SECONDS: float = float(os.environ.get("REASONING_TIMEOUT_SECONDS", "25"))

# DSNs for the two seeded institution Postgres sources (flagship: one
# PostgresProvider, two deliberately-different schemas, proving the integration story
# generalises). NOT in REQUIRED_ENV_VARS — the app boots without them and the
# institution connectors simply return a graceful 502 until a DB is reachable.
# Defaults connect as the SELECT-only ``umraa_reader`` role the seeds create (SEC-01:
# read-only role + the connector's SET TRANSACTION READ ONLY — both clauses), against
# the docker-compose institution_a/institution_b services. Deployments override with a
# real credential.
INSTITUTION_A_DSN: str = os.environ.get(
    "INSTITUTION_A_DSN", "postgresql://umraa_reader:umraa_reader@localhost:5433/institution_a"
)
INSTITUTION_B_DSN: str = os.environ.get(
    "INSTITUTION_B_DSN", "postgresql://umraa_reader:umraa_reader@localhost:5434/institution_b"
)


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
