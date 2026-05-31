from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.cache import repo
from backend.app.cache.models import AuditEvent, Base, CachedResource, EvidenceCard

_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _make_session():
    engine = create_async_engine(_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# save-twice-no-duplicate
# ---------------------------------------------------------------------------


def test_upsert_resource_no_duplicate():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            kwargs = dict(
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                body={"status": "active"},
                source_provider="mock",
            )
            await repo.upsert_resource(sess, **kwargs)
            await repo.upsert_resource(sess, **{**kwargs, "body": {"status": "resolved"}})

            count = (
                await sess.execute(select(func.count()).select_from(CachedResource))
            ).scalar_one()
            assert count == 1

            row = await sess.get(CachedResource, ("p1", "Condition", "c1"))
            assert row is not None
            assert row.body == {"status": "resolved"}
        await engine.dispose()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# audit written on read
# ---------------------------------------------------------------------------


def test_audit_written_on_read():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            await repo.upsert_resource(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                body={},
                source_provider="mock",
            )
            await repo.get_resource(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                actor="test-user",
            )

            count = (await sess.execute(select(func.count()).select_from(AuditEvent))).scalar_one()
            assert count == 1

            event = (await sess.execute(select(AuditEvent))).scalar_one()
            assert event.event_type == "resource_read"
            assert event.resource_ref == "Condition/c1"
            assert event.patient_id == "p1"
            assert event.actor == "test-user"
        await engine.dispose()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# evidence round-trip
# ---------------------------------------------------------------------------


def test_evidence_round_trip():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            body = {
                "drug": "warfarin",
                "interaction": "aspirin",
                "severity": "major",
            }
            await repo.upsert_evidence_card(sess, evidence_id="ev-001", kind="ddinter", body=body)

            # second upsert with updated body — still one row
            updated = {**body, "severity": "moderate"}
            await repo.upsert_evidence_card(
                sess, evidence_id="ev-001", kind="ddinter", body=updated
            )
            count = (
                await sess.execute(select(func.count()).select_from(EvidenceCard))
            ).scalar_one()
            assert count == 1

            row = await repo.get_evidence_card(sess, evidence_id="ev-001", actor="test-user")
            assert row is not None
            assert row.kind == "ddinter"
            assert row.body == updated

            # get_evidence_card wrote an audit row
            audit_count = (
                await sess.execute(select(func.count()).select_from(AuditEvent))
            ).scalar_one()
            assert audit_count == 1
        await engine.dispose()

    asyncio.run(run())
