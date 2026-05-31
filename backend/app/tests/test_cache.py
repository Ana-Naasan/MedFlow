from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.cache import repo
from backend.app.cache.models import AuditEvent, Base, CachedResource, EvidenceCard
from backend.app.cache.repo import CacheStatus

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


# ---------------------------------------------------------------------------
# TTL on upsert (CACHE-02)
# ---------------------------------------------------------------------------


def test_upsert_sets_and_updates_expires_at():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            row = await repo.upsert_resource(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                body={"v": 1},
                source_provider="mock",
                ttl_seconds=60,
            )
            first_expiry = row.expires_at
            assert first_expiry is not None and first_expiry > datetime.now(UTC)

            # re-upsert with a TTL pushes expires_at further out
            row = await repo.upsert_resource(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                body={"v": 2},
                source_provider="mock",
                ttl_seconds=600,
            )
            assert row.expires_at > first_expiry
        await engine.dispose()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# refresh-on-read (CACHE-02/03)
# ---------------------------------------------------------------------------


async def _seed(sess, *, ttl_seconds=None, expires_at="__keep__"):
    """Insert one cached resource, optionally forcing a specific expires_at."""
    row = await repo.upsert_resource(
        sess,
        patient_id="p1",
        resource_type="Condition",
        resource_id="c1",
        body={"v": "cached"},
        source_provider="mock",
        ttl_seconds=ttl_seconds,
    )
    if expires_at != "__keep__":
        row.expires_at = expires_at
        await sess.flush()
    return row


def test_get_or_refresh_fresh_is_hit_without_fetch():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            await _seed(sess, ttl_seconds=3600)  # fresh
            called = False

            async def fetcher():
                nonlocal called
                called = True
                return {"v": "new"}

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.HIT
            assert called is False
            assert row.body == {"v": "cached"}
            # audit still written on read
            assert (
                await sess.execute(select(func.count()).select_from(AuditEvent))
            ).scalar_one() == 1
        await engine.dispose()

    asyncio.run(run())


def test_get_or_refresh_no_ttl_is_hit():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            await _seed(sess)  # expires_at is NULL → never expires

            async def fetcher():
                return {"v": "new"}

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.HIT
            assert row.body == {"v": "cached"}
        await engine.dispose()

    asyncio.run(run())


def test_get_or_refresh_expired_refetches():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            await _seed(sess, expires_at=datetime.now(UTC) - timedelta(seconds=1))  # stale

            async def fetcher():
                return {"v": "fresh"}

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.REFRESH
            assert row.body == {"v": "fresh"}
            assert row.expires_at > datetime.now(UTC)
        await engine.dispose()

    asyncio.run(run())


def test_get_or_refresh_miss_then_fetch():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:

            async def fetcher():
                return {"v": "fetched"}

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="missing",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.REFRESH
            assert row is not None and row.body == {"v": "fetched"}
        await engine.dispose()

    asyncio.run(run())


def test_get_or_refresh_miss_and_source_empty_is_miss():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:

            async def fetcher():
                return None

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="missing",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.MISS
            assert row is None
        await engine.dispose()

    asyncio.run(run())


def test_get_or_refresh_stale_and_source_empty_serves_stale():
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            await _seed(sess, expires_at=datetime.now(UTC) - timedelta(seconds=1))

            async def fetcher():
                return None  # source had nothing new

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.HIT
            assert row.body == {"v": "cached"}
        await engine.dispose()

    asyncio.run(run())


def test_get_or_refresh_lost_lock_serves_stale(monkeypatch):
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:
            await _seed(sess, expires_at=datetime.now(UTC) - timedelta(seconds=1))

            async def lose(_session, _key):
                return False

            monkeypatch.setattr(repo, "_try_advisory_xact_lock", lose)
            fetched = False

            async def fetcher():
                nonlocal fetched
                fetched = True
                return {"v": "fresh"}

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="c1",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.HIT  # served stale, did not re-pull
            assert fetched is False
            assert row.body == {"v": "cached"}
        await engine.dispose()

    asyncio.run(run())


def test_get_or_refresh_lost_lock_and_no_cache_is_miss(monkeypatch):
    async def run():
        engine, factory = await _make_session()
        async with factory() as sess:

            async def lose(_session, _key):
                return False

            monkeypatch.setattr(repo, "_try_advisory_xact_lock", lose)

            async def fetcher():
                return {"v": "fresh"}

            row, status = await repo.get_or_refresh(
                sess,
                patient_id="p1",
                resource_type="Condition",
                resource_id="missing",
                actor="u",
                fetcher=fetcher,
                source_provider="mock",
                ttl_seconds=3600,
            )
            assert status is CacheStatus.MISS
            assert row is None
        await engine.dispose()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# advisory lock dialect handling
# ---------------------------------------------------------------------------


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeDialect:
    name = "postgresql"


class _FakeBind:
    dialect = _FakeDialect()


class _FakePGSession:
    """Minimal stand-in exercising the Postgres advisory-lock branch."""

    def __init__(self, value):
        self.bind = _FakeBind()
        self._value = value
        self.executed = None

    async def execute(self, stmt, params=None):
        self.executed = (str(stmt), params)
        return _FakeResult(self._value)


def test_advisory_lock_postgres_branch_acquired():
    sess = _FakePGSession(True)
    got = asyncio.run(repo._try_advisory_xact_lock(sess, 123))
    assert got is True
    assert "pg_try_advisory_xact_lock" in sess.executed[0]
    assert sess.executed[1] == {"k": 123}


def test_advisory_lock_postgres_branch_not_acquired():
    sess = _FakePGSession(False)
    assert asyncio.run(repo._try_advisory_xact_lock(sess, 7)) is False


def test_advisory_lock_unbound_session_grants():
    class _Unbound:
        bind = None

    assert asyncio.run(repo._try_advisory_xact_lock(_Unbound(), 1)) is True
