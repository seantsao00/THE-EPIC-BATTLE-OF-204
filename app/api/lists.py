from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_session_local
from ..models import DomainList

router = APIRouter(prefix="/api/lists", tags=["lists"])


class ListRequest(BaseModel):
    domain: str
    list_type: str  # 'whitelist' or 'blacklist'


@router.post("/")
def add_to_list(item: ListRequest, db: Session = Depends(get_session_local), user=Depends(get_current_user)):
    dl = DomainList(domain=item.domain, list_type=item.list_type)
    db.add(dl)
    db.commit()
    return {"status": "ok"}


@router.delete("/")
def remove_from_list(item: ListRequest, db: Session = Depends(get_session_local), user=Depends(get_current_user)):
    dl = db.query(DomainList).filter_by(domain=item.domain, list_type=item.list_type).first()
    if dl:
        db.delete(dl)
        db.commit()
    return {"status": "ok"}
