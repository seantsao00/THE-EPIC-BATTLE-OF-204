import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlmodel import func, or_, select
from sqlmodel.sql.expression import col

from ..auth import UserDep
from ..database import SessionDep
from ..models import DomainList, ListSource, ListType, MetaResponse

router = APIRouter(prefix="/api/lists", tags=["lists"])


class DomainRequest(BaseModel):
    domain: str

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        pattern = re.compile(
            r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,}$')
        if not pattern.match(v):
            raise ValueError('Invalid domain name')
        return v


class DomainListResponse(BaseModel):
    domains: list[DomainList]
    meta: MetaResponse


@router.get("/{source}/{list_type}/domains", response_model=DomainListResponse)
def list_domains_in_list(
    source: ListSource,
    list_type: ListType,
    session: SessionDep,
    current_user: UserDep,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip for pagination")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of records to return")] = 100,
) -> dict:
    statement = select(DomainList).where(DomainList.source == source,
                                         DomainList.list_type == list_type)
    total = session.exec(
        select(func.count())
        .select_from(DomainList)
        .where(DomainList.source == source, DomainList.list_type == list_type)).one()
    if source is ListSource.llm:
        statement = statement.where(or_(col(DomainList.expires_at) is None,
                                        DomainList.expires_at > func.now()))
    domains = session.exec(
        statement.offset(offset).limit(limit)
    ).all()
    return {
        "domains": domains,
        "meta": {
            "total": total,
            "offset": offset,
            "limit": limit
        }
    }


class StatusResponse(BaseModel):
    status: str


@router.post(
    "/manual/{list_type}/domains",
    status_code=status.HTTP_201_CREATED,
    response_model=StatusResponse,
    responses={
        201: {"description": "Domain added successfully"},
        409: {"description": "Domain already in list"},
    },
)
def add_domain_to_manual_list(
    list_type: ListType,
    domain_request: DomainRequest,
    session: SessionDep,
    current_user: UserDep
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
    response_model=StatusResponse,
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
    current_user: UserDep,
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
