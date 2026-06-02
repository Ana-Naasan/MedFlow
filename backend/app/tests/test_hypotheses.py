"""Audit and cascade tests for hypothesis confirm/dismiss endpoints."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.cache import repo
from backend.app.cache.models import AuditEvent
from backend.app.main import app


@pytest.fixture(autouse=True)
def required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


_HEADERS = {"Authorization": "Bearer PLACEHOLDER"}


# ── repo-level helpers ───────────────────────────────────────────────────────


def _run(coro):
    """Run an async coroutine in a fresh event loop (no TestClient involved)."""
    return asyncio.run(coro)


# ── repo-level tests ─────────────────────────────────────────────────────────


def test_confirm_writes_audit():
    with TestClient(app):  # starts the lifespan → creates DB tables
        factory = app.state.session_factory

        async def _run_inner():
            async with factory() as session:
                async with session.begin():
                    row = await repo.upsert_hypothesis(
                        session,
                        id="hyp-test-confirm",
                        patient_id="pat-test",
                        title="Test hypothesis",
                    )
                    confirmed = await repo.confirm_hypothesis(
                        session, id=row.id, actor="doctor", patient_id="pat-test"
                    )
                    result = await session.execute(
                        select(AuditEvent).where(AuditEvent.event_type == "hypothesis_confirmed")
                    )
                    events = result.scalars().all()
            return confirmed, events

        confirmed, events = asyncio.run(_run_inner())
    assert confirmed is not None
    assert confirmed.status == "confirmed"
    assert len(events) == 1


def test_dismiss_writes_audit_and_hides_similar_by_group():
    with TestClient(app):
        factory = app.state.session_factory

        async def _run_inner():
            async with factory() as session:
                async with session.begin():
                    for i in range(3):
                        await repo.upsert_hypothesis(
                            session,
                            id=f"hyp-grp-{i}",
                            patient_id="pat-grp",
                            title=f"Bleed risk {i}",
                            group="drug:warfarin;risk:bleeding",
                        )
                    dismissed_ids = await repo.dismiss_hypothesis(
                        session, id="hyp-grp-0", actor="doctor", patient_id="pat-grp"
                    )
                    result = await session.execute(
                        select(AuditEvent).where(AuditEvent.event_type == "hypothesis_dismissed")
                    )
                    events = result.scalars().all()
            return dismissed_ids, events

        dismissed_ids, events = asyncio.run(_run_inner())
    assert set(dismissed_ids) == {"hyp-grp-0", "hyp-grp-1", "hyp-grp-2"}
    assert len(events) == 1


def test_confirm_is_idempotent_no_duplicate_audit():
    """Confirming an already-confirmed hypothesis is a no-op: status stays
    confirmed and no second audit event is written."""
    with TestClient(app):
        factory = app.state.session_factory

        async def _run_inner():
            async with factory() as session:
                async with session.begin():
                    await repo.upsert_hypothesis(
                        session, id="hyp-idem-c", patient_id="pat-idem-c", title="T"
                    )
                    await repo.confirm_hypothesis(
                        session, id="hyp-idem-c", actor="doctor", patient_id="pat-idem-c"
                    )
                    again = await repo.confirm_hypothesis(
                        session, id="hyp-idem-c", actor="doctor", patient_id="pat-idem-c"
                    )
                    result = await session.execute(
                        select(AuditEvent).where(AuditEvent.resource_ref == "hypothesis/hyp-idem-c")
                    )
                    events = result.scalars().all()
            return again, events

        again, events = asyncio.run(_run_inner())
    assert again is not None
    assert again.status == "confirmed"
    assert len(events) == 1  # the second confirm wrote no duplicate audit


def test_dismiss_is_idempotent_no_duplicate_audit():
    """Re-dismissing still returns the dismissed set (endpoint stays 200) but
    writes no duplicate audit event."""
    with TestClient(app):
        factory = app.state.session_factory

        async def _run_inner():
            async with factory() as session:
                async with session.begin():
                    await repo.upsert_hypothesis(
                        session,
                        id="hyp-idem-d",
                        patient_id="pat-idem-d",
                        title="T",
                        group="g:idem",
                    )
                    first = await repo.dismiss_hypothesis(
                        session, id="hyp-idem-d", actor="doctor", patient_id="pat-idem-d"
                    )
                    second = await repo.dismiss_hypothesis(
                        session, id="hyp-idem-d", actor="doctor", patient_id="pat-idem-d"
                    )
                    result = await session.execute(
                        select(AuditEvent).where(
                            AuditEvent.event_type == "hypothesis_dismissed",
                            AuditEvent.patient_id == "pat-idem-d",
                        )
                    )
                    events = result.scalars().all()
            return first, second, events

        first, second, events = asyncio.run(_run_inner())
    assert "hyp-idem-d" in first
    assert set(second) == set(first)  # re-dismiss returns the dismissed set (200, not 404)
    assert len(events) == 1  # but no duplicate audit


def test_dismiss_falls_back_to_title_when_no_group():
    with TestClient(app):
        factory = app.state.session_factory

        async def _run_inner():
            async with factory() as session:
                async with session.begin():
                    for i in range(2):
                        await repo.upsert_hypothesis(
                            session,
                            id=f"hyp-title-{i}",
                            patient_id="pat-title",
                            title="Exact same title",
                        )
                    dismissed_ids = await repo.dismiss_hypothesis(
                        session, id="hyp-title-0", actor="doctor", patient_id="pat-title"
                    )
            return dismissed_ids

        dismissed_ids = asyncio.run(_run_inner())
    assert set(dismissed_ids) == {"hyp-title-0", "hyp-title-1"}


def test_confirm_returns_none_for_unknown_id():
    with TestClient(app):
        factory = app.state.session_factory

        async def _run_inner():
            async with factory() as session:
                async with session.begin():
                    return await repo.confirm_hypothesis(
                        session, id="nonexistent", actor="doctor", patient_id="pat-x"
                    )

        result = asyncio.run(_run_inner())
    assert result is None


def test_dismiss_returns_empty_for_unknown_id():
    with TestClient(app):
        factory = app.state.session_factory

        async def _run_inner():
            async with factory() as session:
                async with session.begin():
                    return await repo.dismiss_hypothesis(
                        session, id="nonexistent", actor="doctor", patient_id="pat-x"
                    )

        result = asyncio.run(_run_inner())
    assert result == []


# ── HTTP-level tests ─────────────────────────────────────────────────────────


def test_http_confirm_writes_audit():
    with TestClient(app) as client:
        factory = app.state.session_factory

        # Seed the hypothesis directly
        async def _seed():
            async with factory() as session:
                async with session.begin():
                    await repo.upsert_hypothesis(
                        session,
                        id="hyp-http-confirm",
                        patient_id="pat-http",
                        title="HTTP test hypothesis",
                    )

        asyncio.run(_seed())

        resp = client.post(
            "/hypotheses/hyp-http-confirm/confirm",
            json={"patient_id": "pat-http"},
            headers=_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    select(AuditEvent).where(AuditEvent.event_type == "hypothesis_confirmed")
                )
                return result.scalars().all()

        events = asyncio.run(_check())
    assert len(events) >= 1


def test_http_dismiss_writes_audit():
    with TestClient(app) as client:
        factory = app.state.session_factory

        async def _seed():
            async with factory() as session:
                async with session.begin():
                    await repo.upsert_hypothesis(
                        session,
                        id="hyp-http-dismiss",
                        patient_id="pat-http-d",
                        title="HTTP dismiss test",
                    )

        asyncio.run(_seed())

        resp = client.post(
            "/hypotheses/hyp-http-dismiss/dismiss",
            json={"patient_id": "pat-http-d"},
            headers=_HEADERS,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "dismissed"
        assert "hyp-http-dismiss" in body["dismissed_ids"]

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    select(AuditEvent).where(AuditEvent.event_type == "hypothesis_dismissed")
                )
                return result.scalars().all()

        events = asyncio.run(_check())
    assert len(events) >= 1


def test_http_confirm_and_dismiss_audit_actor_is_token_subject():
    # API-07: confirm/dismiss audit events record the token subject, not actor="doctor".
    from backend.app.api.auth import dev_token_subject

    expected = dev_token_subject("PLACEHOLDER")
    with TestClient(app) as client:
        factory = app.state.session_factory

        async def _seed():
            async with factory() as session:
                async with session.begin():
                    await repo.upsert_hypothesis(
                        session, id="hyp-actor-confirm", patient_id="pat-actor", title="C"
                    )
                    await repo.upsert_hypothesis(
                        session, id="hyp-actor-dismiss", patient_id="pat-actor", title="D"
                    )

        asyncio.run(_seed())

        confirm = client.post(
            "/hypotheses/hyp-actor-confirm/confirm",
            json={"patient_id": "pat-actor"},
            headers=_HEADERS,
        )
        dismiss = client.post(
            "/hypotheses/hyp-actor-dismiss/dismiss",
            json={"patient_id": "pat-actor"},
            headers=_HEADERS,
        )
        assert confirm.status_code == 200
        assert dismiss.status_code == 200

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    select(AuditEvent).where(
                        AuditEvent.event_type.in_(["hypothesis_confirmed", "hypothesis_dismissed"])
                    )
                )
                return result.scalars().all()

        events = asyncio.run(_check())
    actors = {e.actor for e in events}
    assert actors == {expected}
    assert "doctor" not in actors


def test_http_confirm_404_for_missing():
    with TestClient(app) as client:
        resp = client.post(
            "/hypotheses/no-such-id/confirm",
            json={"patient_id": "pat-x"},
            headers=_HEADERS,
        )
    assert resp.status_code == 404


def test_http_dismiss_404_for_missing():
    with TestClient(app) as client:
        resp = client.post(
            "/hypotheses/no-such-id/dismiss",
            json={"patient_id": "pat-x"},
            headers=_HEADERS,
        )
    assert resp.status_code == 404
