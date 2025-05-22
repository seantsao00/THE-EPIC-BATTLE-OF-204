from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import DomainList

router = APIRouter(prefix="/api/lists", tags=["lists"])


class DomainRequest(BaseModel):
    domain: str


@router.get("/{list_type}/domains")
def list_domains_in_list(
    list_type: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)]
):
    domains = db.query(DomainList).filter_by(list_type=list_type).all()
    return domains


@router.post(
    "/{list_type}/domains",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Domain added successfully"},
        409: {"description": "Domain already in list"},
    },
)
def add_domain_to_list(
    list_type: str,
    req: DomainRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)]
):
    exists = db.query(DomainList).filter_by(domain=req.domain).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Domain already in list")

    dl = DomainList(domain=req.domain, list_type=list_type)
    db.add(dl)
    db.commit()
    return {"status": "created"}


@router.delete(
    "/{list_type}/domains/{domain}",
    responses={
        200: {"description": "Domain deleted successfully"},
        404: {"description": "Domain not found in list"},
    },
)
def remove_domain_from_list(
    list_type: str,
    domain: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)],
):
    dl = db.query(DomainList).filter_by(domain=domain, list_type=list_type).first()
    if not dl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Domain not found in list")
    db.delete(dl)
    db.commit()
    return {"status": "deleted"}
