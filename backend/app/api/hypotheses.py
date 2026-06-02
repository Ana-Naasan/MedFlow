from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth import require_dev_token
from backend.app.cache import repo
from backend.app.dtos import (
    HypothesisActionRequest,
    HypothesisConfirmResponse,
    HypothesisDismissResponse,
)

hypotheses_router = APIRouter(
    prefix="/hypotheses",
    tags=["hypotheses"],
    dependencies=[Depends(require_dev_token)],
)


async def _get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    factory = request.app.state.session_factory
    async with factory() as session:
        async with session.begin():
            yield session


@hypotheses_router.post("/{id}/confirm")
async def confirm_hypothesis(
    id: str,
    body: HypothesisActionRequest,
    db: AsyncSession = Depends(_get_db),  # noqa: B008
    subject: str = Depends(require_dev_token),  # noqa: B008
) -> HypothesisConfirmResponse:
    row = await repo.confirm_hypothesis(db, id=id, actor=subject, patient_id=body.patient_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hypothesis not found")
    return HypothesisConfirmResponse(id=row.id, status=row.status)


@hypotheses_router.post("/{id}/dismiss")
async def dismiss_hypothesis(
    id: str,
    body: HypothesisActionRequest,
    db: AsyncSession = Depends(_get_db),  # noqa: B008
    subject: str = Depends(require_dev_token),  # noqa: B008
) -> HypothesisDismissResponse:
    dismissed_ids = await repo.dismiss_hypothesis(
        db, id=id, actor=subject, patient_id=body.patient_id
    )
    if not dismissed_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hypothesis not found")
    # Echo the SERVED (un-prefixed) ids so the provider UI can match the
    # dismissed cards (it keys resolved[hypothesis.id]); storage namespaces with
    # ``{patient_id}:`` for cross-patient collision safety.
    prefix = f"{body.patient_id}:"
    served_ids = [d[len(prefix) :] if d.startswith(prefix) else d for d in dismissed_ids]
    return HypothesisDismissResponse(id=id, status="dismissed", dismissed_ids=served_ids)
