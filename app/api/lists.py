from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from ..auth import get_current_user
from ..database import get_db
from ..models import DomainList, ListSource, ListType

router = APIRouter(prefix="/api/lists", tags=["lists"])


class DomainRequest(BaseModel):
    domain: str


@router.get("/{source}/{list_type}/domains")
def list_domains_in_list(
    source: ListSource,
    list_type: ListType,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)]
):
    q = db.query(DomainList).filter_by(source=source.value, list_type=list_type.value)
    if source is ListSource.llm:
        q = q.filter((DomainList.expires_at == None) | (DomainList.expires_at > func.now()))
    domains = q.all()
    return domains


@router.post(
    "/manual/{list_type}/domains",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Domain added successfully"},
        409: {"description": "Domain already in list"},
    },
)
def add_domain_to_manual_list(
    list_type: ListType,
    req: DomainRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)]
):
    exists = db.query(DomainList).filter_by(domain=req.domain).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Domain {req.domain} already exists in {list_type.value} list with source {exists.source.value}")

    dl = DomainList(domain=req.domain, list_type=list_type.value, source="manual", expires_at=None)
    db.add(dl)
    db.commit()
    return {"status": "created"}


@router.delete(
    "/{source}/{list_type}/domains/{domain}",
    responses={
        200: {"description": "Domain deleted successfully"},
        404: {"description": "Domain not found in list"},
    },
)
def remove_domain_from_list(
    source: ListSource,
    list_type: ListType,
    domain: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(get_current_user)],
):
    q = db.query(DomainList).filter_by(
        domain=domain, list_type=list_type.value, source=source.value)
    if source is ListSource.llm:
        q = q.filter((DomainList.expires_at == None) | (DomainList.expires_at > func.now()))
    dl = q.first()
    if not dl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Domain not found in list")
    db.delete(dl)
    db.commit()
    return {"status": "deleted"}
