from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_session_local
from ..models import DomainLog

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("/")
def list_domains(db: Session = Depends(get_session_local), user=Depends(get_current_user)):
    return db.query(DomainLog).order_by(DomainLog.last_seen.desc()).all()
