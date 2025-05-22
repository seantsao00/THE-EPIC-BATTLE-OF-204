from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlmodel import func, select

from ..auth import UserDep
from ..database import SessionDep
from ..models import DomainLog, MetaResponse

router = APIRouter(prefix="/api/domain-logs", tags=["domain-logs"])


class DomainLogListResponse(BaseModel):
    logs: list[DomainLog]
    meta: MetaResponse


@router.get("", response_model=DomainLogListResponse)
def list_domain_logs(
    session: SessionDep,
    current_user: UserDep,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip for pagination")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of records to return")] = 100,
):
    total = session.exec(select(func.count()).select_from(DomainLog)).one()
    logs = session.exec(
        select(DomainLog)
        .order_by(getattr(DomainLog, 'timestamp').desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "logs": logs,
        "meta": {
            "total": total,
            "offset": offset,
            "limit": limit
        }
    }
