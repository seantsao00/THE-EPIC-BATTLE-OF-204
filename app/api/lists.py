from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import DomainList

router = APIRouter(prefix="/api/lists", tags=["lists"])


class ListRequest(BaseModel):
    domain: str
    list_type: str  # 'whitelist' or 'blacklist'


@router.post("")
def add_to_list(
    item: ListRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)]
):
    dl = DomainList(domain=item.domain, list_type=item.list_type)
    db.add(dl)
    db.commit()
    return {"status": "ok"}


@router.delete("")
def remove_from_list(
    item: ListRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)]
):
    dl = db.query(DomainList).filter_by(domain=item.domain, list_type=item.list_type).first()
    if dl:
        db.delete(dl)
        db.commit()
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=404, detail="Domain not found in list")
