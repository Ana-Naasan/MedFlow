"""Smoke tests: the google-genai SDK is installed and importable."""


def test_google_genai_sdk_importable() -> None:
    """google-genai must be installed (added in Subtask 1)."""
    import google.genai  # noqa: F401


def test_google_genai_has_async_client() -> None:
    """The SDK exposes a Client class (sync client with underlying aio support)."""
    from google.genai import Client

    assert Client is not None
