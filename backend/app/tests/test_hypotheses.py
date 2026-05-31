"""Tests for confirm/dismiss hypothesis endpoints — verifies audit events are written."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.cache import repo
from backend.app.cache.models import AuditEvent, Base, HypothesisRecord


@pytest.fixture(autouse=True)
def _set_dev_token(monkeypatch):
    monkeypatch.setenv("DEV_TOKEN", "test-token")
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake")
    monkeypatch.setenv("OPENFDA_API_KEY", "fake")


# ---------------------------------------------------------------------------
# Repo-level unit tests (no HTTP layer)
# ---------------------------------------------------------------------------


def _make_engine_and_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, factory


def test_confirm_writes_audit():
    async def run():
        engine, factory = _make_engine_and_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as sess:
            await repo.upsert_hypothesis(
                sess,
                id="hyp-c1",
                patient_id="p1",
                title="Drug risk",
                group="drug:aspirin;risk:bleeding",
            )
            await sess.commit()

        async with factory() as sess:
            async with sess.begin():
                row = await repo.confirm_hypothesis(
                    sess, id="hyp-c1", actor="doctor", patient_id="p1"
                )

        assert row is not None
        assert row.status == "confirmed"

        async with factory() as sess:
            count = (
                await sess.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.event_type == "hypothesis_confirmed")
                )
            ).scalar_one()
            assert count == 1
            event = (await sess.execute(select(AuditEvent))).scalar_one()
            assert event.resource_ref == "Hypothesis/hyp-c1"
            assert event.patient_id == "p1"
            assert event.actor == "doctor"

        await engine.dispose()

    asyncio.run(run())


def test_dismiss_writes_audit_and_hides_similar_by_group():
    async def run():
        engine, factory = _make_engine_and_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as sess:
            async with sess.begin():
                await repo.upsert_hypothesis(
                    sess,
                    id="hyp-d1",
                    patient_id="p1",
                    title="Drug risk",
                    group="drug:aspirin;risk:bleeding",
                )
                await repo.upsert_hypothesis(
                    sess,
                    id="hyp-d2",
                    patient_id="p1",
                    title="Different title",
                    group="drug:aspirin;risk:bleeding",
                )
                await repo.upsert_hypothesis(
                    sess, id="hyp-d3", patient_id="p1", title="Unrelated", group="other:group"
                )

        async with factory() as sess:
            async with sess.begin():
                dismissed_ids = await repo.dismiss_hypothesis(
                    sess, id="hyp-d1", actor="doctor", patient_id="p1"
                )

        # Both hypotheses in the same group are dismissed; the unrelated one is not.
        assert set(dismissed_ids) == {"hyp-d1", "hyp-d2"}

        async with factory() as sess:
            unrelated = await sess.get(HypothesisRecord, "hyp-d3")
            assert unrelated is not None
            assert unrelated.status == "pending"

            count = (
                await sess.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.event_type == "hypothesis_dismissed")
                )
            ).scalar_one()
            assert count == 1

        await engine.dispose()

    asyncio.run(run())


def test_dismiss_falls_back_to_title_when_no_group():
    async def run():
        engine, factory = _make_engine_and_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as sess:
            async with sess.begin():
                await repo.upsert_hypothesis(
                    sess, id="hyp-t1", patient_id="p1", title="Shared title", group=None
                )
                await repo.upsert_hypothesis(
                    sess, id="hyp-t2", patient_id="p1", title="Shared title", group=None
                )
                await repo.upsert_hypothesis(
                    sess, id="hyp-t3", patient_id="p1", title="Other title", group=None
                )

        async with factory() as sess:
            async with sess.begin():
                dismissed_ids = await repo.dismiss_hypothesis(
                    sess, id="hyp-t1", actor="doctor", patient_id="p1"
                )

        assert set(dismissed_ids) == {"hyp-t1", "hyp-t2"}

        await engine.dispose()

    asyncio.run(run())


def test_confirm_returns_none_for_unknown_id():
    async def run():
        engine, factory = _make_engine_and_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as sess:
            async with sess.begin():
                result = await repo.confirm_hypothesis(
                    sess, id="ghost", actor="doc", patient_id="p1"
                )

        assert result is None
        await engine.dispose()

    asyncio.run(run())


def test_dismiss_returns_empty_for_unknown_id():
    async def run():
        engine, factory = _make_engine_and_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as sess:
            async with sess.begin():
                result = await repo.dismiss_hypothesis(
                    sess, id="ghost", actor="doc", patient_id="p1"
                )

        assert result == []
        await engine.dispose()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# HTTP-level tests
# ---------------------------------------------------------------------------


def _make_app_with_db():
    engine, factory = _make_engine_and_factory()
    return engine, factory


def test_http_confirm_writes_audit():
    async def run():
        engine, factory = _make_engine_and_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as sess:
            async with sess.begin():
                await repo.upsert_hypothesis(
                    sess, id="http-hyp-1", patient_id="pat-http", title="T", group=None
                )

        from backend.app.main import create_app

        app = create_app()

        with TestClient(app) as client:
            # Override factory after lifespan so requests use our seeded DB.
            app.state.session_factory = factory
            resp = client.post(
                "/hypotheses/http-hyp-1/confirm",
                json={"patient_id": "pat-http"},
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

        async with factory() as sess:
            count = (
                await sess.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.event_type == "hypothesis_confirmed")
                )
            ).scalar_one()
            assert count == 1

        await engine.dispose()

    asyncio.run(run())


def test_http_dismiss_writes_audit():
    async def run():
        engine, factory = _make_engine_and_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with factory() as sess:
            async with sess.begin():
                await repo.upsert_hypothesis(
                    sess, id="http-hyp-2", patient_id="pat-http", title="T2", group=None
                )

        from backend.app.main import create_app

        app = create_app()

        with TestClient(app) as client:
            # Override factory after lifespan so requests use our seeded DB.
            app.state.session_factory = factory
            resp = client.post(
                "/hypotheses/http-hyp-2/dismiss",
                json={"patient_id": "pat-http"},
                headers={"Authorization": "Bearer test-token"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "dismissed"
        assert "http-hyp-2" in body["dismissed_ids"]

        async with factory() as sess:
            count = (
                await sess.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.event_type == "hypothesis_dismissed")
                )
            ).scalar_one()
            assert count == 1

        await engine.dispose()

    asyncio.run(run())


def test_http_confirm_404_for_missing():
    from backend.app.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/hypotheses/nonexistent/confirm",
            json={"patient_id": "p1"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert resp.status_code == 404


def test_http_dismiss_404_for_missing():
    from backend.app.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/hypotheses/nonexistent/dismiss",
            json={"patient_id": "p1"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert resp.status_code == 404
