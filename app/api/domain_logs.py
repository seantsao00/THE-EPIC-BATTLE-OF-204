from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import DomainLog

router = APIRouter(prefix="/api/domain-logs", tags=["domain-logs"])


@router.get("")
def list_domain_logs(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)]
):
    return db.query(DomainLog).order_by(DomainLog.last_seen.desc()).all()
