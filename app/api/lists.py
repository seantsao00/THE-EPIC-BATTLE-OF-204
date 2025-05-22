from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import func, or_, select
from sqlmodel.sql.expression import col

from ..auth import get_current_user
from ..database import SessionDep
from ..models import DomainList, ListSource, ListType

router = APIRouter(prefix="/api/lists", tags=["lists"])


class DomainRequest(BaseModel):
    domain: str


@router.get("/{source}/{list_type}/domains")
def list_domains_in_list(
    source: ListSource,
    list_type: ListType,
    session: SessionDep,
    current_user: Annotated[object, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0, description="Number of records to skip for pagination")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of records to return")] = 100,
) -> Sequence[DomainList]:
    statement = select(DomainList).where(DomainList.source == source,
                                         DomainList.list_type == list_type)
    if source is ListSource.llm:
        statement = statement.where(or_(col(DomainList.expires_at) is None,
                                        DomainList.expires_at > func.now()))
    domains = session.exec(
        statement.offset(skip).limit(limit)
    ).all()
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
    domain_request: DomainRequest,
    session: SessionDep,
    current_user: Annotated[object, Depends(get_current_user)]
):
    existing_domain = session.exec(select(DomainList)
                                   .where(DomainList.domain == domain_request.domain)).first()
    if existing_domain:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Domain {domain_request.domain} already exists in {list_type.value} list with source {existing_domain.source.value}")

    domain_list = DomainList(domain=domain_request.domain, list_type=list_type,
                             source=ListSource.manual, expires_at=None)
    session.add(domain_list)
    session.commit()
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
    session: SessionDep,
    current_user: Annotated[object, Depends(get_current_user)],
):
    statement = select(DomainList).where(DomainList.domain == domain,
                                         DomainList.list_type == list_type, DomainList.source == source)
    if source is ListSource.llm:
        statement = statement.where(or_(col(DomainList.expires_at) is None,
                                        DomainList.expires_at > func.now()))
    domain_list = session.exec(statement).first()
    if not domain_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Domain not found in list")
    session.delete(domain_list)
    session.commit()
    return {"status": "deleted"}
