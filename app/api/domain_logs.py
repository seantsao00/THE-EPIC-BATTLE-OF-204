from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, Query
from sqlmodel import select

from ..auth import get_current_user
from ..database import SessionDep
from ..models import DomainLog

router = APIRouter(prefix="/api/domain-logs", tags=["domain-logs"])


@router.get("")
def list_domain_logs(
    session: SessionDep,
    current_user: Annotated[object, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0, description="Number of records to skip for pagination")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of records to return")] = 100,
) -> Sequence[DomainLog]:
    return session.exec(
        select(DomainLog)
        .order_by(getattr(DomainLog, 'timestamp').desc())
        .offset(skip)
        .limit(limit)
    ).all()
