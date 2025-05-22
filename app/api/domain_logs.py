from typing import Annotated, Sequence

from fastapi import APIRouter, Depends
from sqlmodel import select

from ..auth import get_current_user
from ..database import SessionDep
from ..models import DomainLog

router = APIRouter(prefix="/api/domain-logs", tags=["domain-logs"])


@router.get("")
def list_domain_logs(
    session: SessionDep,
    current_user: Annotated[object, Depends(get_current_user)]
) -> Sequence[DomainLog]:
    return session.exec(select(DomainLog).order_by(getattr(DomainLog, 'timestamp').desc())).all()
