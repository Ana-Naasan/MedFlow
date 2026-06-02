"""Unit tests for dev-token auth and the audit token-subject (API-07)."""

from __future__ import annotations

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.auth import dev_token_subject, require_dev_token


def test_dev_token_subject_is_deterministic_nonsecret_and_token_specific():
    subject = dev_token_subject("super-secret-token")

    assert subject == dev_token_subject("super-secret-token")  # stable for a given token
    assert subject.startswith("dev:")
    assert "super-secret-token" not in subject  # never embeds the raw secret
    assert dev_token_subject("a-different-token") != subject  # rotates with the token


def test_require_dev_token_returns_the_token_subject(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEV_TOKEN", "tok-abc")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok-abc")

    assert require_dev_token(creds) == dev_token_subject("tok-abc")
