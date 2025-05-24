from typing import Annotated, Sequence

from fastapi import APIRouter, Query
from pydantic import BaseModel
from rapidfuzz import fuzz, process
from sqlmodel import func, select

from ..auth import UserDep
from ..database import SessionDep
from ..models import DomainLog, MetaResponse

router = APIRouter(prefix="/api/domain-logs", tags=["domain-logs"])


class DomainLogListResponse(BaseModel):
    logs: Sequence[DomainLog]
    meta: MetaResponse


@router.get("")
def list_domain_logs(
    session: SessionDep,
    current_user: UserDep,
    keyword: Annotated[str | None, Query(description="Filter logs by keyword")] = None,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip for pagination")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of records to return")] = 10,
) -> DomainLogListResponse:
    if keyword:
        all_logs = session.exec(select(DomainLog)).all()

        matches = process.extract(
            keyword,
            all_logs,
            processor=lambda log: getattr(log, 'domain', None) or str(log),
            scorer=fuzz.token_set_ratio,
            limit=offset + limit
        )

        sorted_logs = [match[0] for match in matches][offset:offset + limit]
        total = len(matches)
        logs = sorted_logs
    else:
        total = session.exec(select(func.count()).select_from(DomainLog)).one()
        logs = session.exec(
            select(DomainLog)
            .order_by(getattr(DomainLog, 'timestamp').desc())
            .offset(offset)
            .limit(limit)
        ).all()
    return DomainLogListResponse(
        logs=logs,
        meta=MetaResponse(
            total=total,
            offset=offset,
            limit=limit
        )
    )
