import re
from typing import Annotated, Sequence

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from rapidfuzz import fuzz, process
from sqlmodel import func, or_, select
from sqlmodel.sql.expression import col

from ..auth import UserDep
from ..database import SessionDep
from ..models import DomainList, ErrorResponse, ListSource, ListType, MetaResponse

router = APIRouter(prefix="/api/lists", tags=["lists"])


class DomainListResponse(BaseModel):
    domains: Sequence[DomainList]
    meta: MetaResponse


@router.get("/{source}/{list_type}/domains")
def list_domains_in_list(
    source: ListSource,
    list_type: ListType,
    session: SessionDep,
    current_user: UserDep,
    keyword: Annotated[str | None, Query(description="Fuzzy filter domains by keyword")] = None,
    offset: Annotated[int, Query(ge=0, description="Number of records to skip for pagination")] = 0,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of records to return")] = 10,
) -> DomainListResponse:
    statement = select(DomainList).where(DomainList.source == source,
                                         DomainList.list_type == list_type)
    if source == ListSource.llm:
        statement = statement.where(or_(DomainList.expires_at == None,
                                        DomainList.expires_at > func.now()))
    if keyword:
        all_domains = session.exec(statement).all()
        
        # Get all matches without limiting to calculate the true total
        all_matches = process.extract(
            keyword,
            all_domains,
            processor=lambda d: getattr(d, 'domain', None) or str(d),
            scorer=fuzz.token_set_ratio,
            limit=None  # No limit to get the full count
        )
        
        # Get the matches needed for pagination
        matches = process.extract(
            keyword,
            all_domains,
            processor=lambda d: getattr(d, 'domain', None) or str(d),
            scorer=fuzz.token_set_ratio,
            limit=offset + limit
        )
        
        sorted_domains = [match[0] for match in matches][offset:offset + limit]
        total = len(all_matches)  # Use all_matches for accurate total
        domains = sorted_domains
    else:
        # Use a count statement that matches our main query filters
        count_stmt = select(func.count()).select_from(DomainList).where(
            DomainList.source == source,
            DomainList.list_type == list_type)
        
        # Apply the same expiration filter only for llm source
        if source == ListSource.llm:
            count_stmt = count_stmt.where(or_(DomainList.expires_at == None,
                                             DomainList.expires_at > func.now()))
        
        total = session.exec(count_stmt).one()
        domains = session.exec(
            statement.offset(offset).limit(limit)
        ).all()
    return DomainListResponse(
        domains=domains,
        meta=MetaResponse(
            total=total,
            offset=offset,
            limit=limit
        )
    )


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


@router.post(
    "/manual/{list_type}/domains",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Domain added successfully"},
        409: {"description": "Domain already exists in list", "model": ErrorResponse},
    },
)
def add_domain_to_manual_list(
    list_type: ListType,
    domain_request: DomainRequest,
    session: SessionDep,
    current_user: UserDep,
):
    existing_domain = session.exec(select(DomainList)
                                   .where(DomainList.domain == domain_request.domain)).first()
    if existing_domain:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain {domain_request.domain} already exists "
            f"in {existing_domain.list_type.value} list "
            f"with source {existing_domain.source.value}")

    domain_list = DomainList(domain=domain_request.domain + ".", list_type=list_type,
                             source=ListSource.manual, expires_at=None)
    session.add(domain_list)
    session.commit()


@router.delete(
    "/{source}/{list_type}/domains/{domain}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Domain deleted successfully"},
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
    statement = select(DomainList).where(
        DomainList.domain == domain,
        DomainList.list_type == list_type,
        DomainList.source == source)
    if source == ListSource.llm:
        statement = statement.where(or_(DomainList.expires_at == None,
                                        DomainList.expires_at > func.now()))
    domain_list = session.exec(statement).first()
    if not domain_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    session.delete(domain_list)
    session.commit()


class ListStatsResponse(BaseModel):
    total_domains: int
    whitelist_count: int
    blacklist_count: int
    manual_count: int
    llm_count: int


@router.get("/stats")
def get_list_stats(session: SessionDep, current_user: UserDep) -> ListStatsResponse:
    total_domains = session.exec(select(func.count()).select_from(DomainList)).one()
    whitelist_count = session.exec(select(func.count())
                                   .select_from(DomainList)
                                   .where(DomainList.list_type == ListType.whitelist)).one()
    blacklist_count = session.exec(select(func.count())
                                   .select_from(DomainList)
                                   .where(DomainList.list_type == ListType.blacklist)).one()
    manual_count = session.exec(select(func.count())
                                .select_from(DomainList)
                                .where(DomainList.source == ListSource.manual)).one()
    llm_count = session.exec(select(func.count())
                             .select_from(DomainList)
                             .where(DomainList.source == ListSource.llm)).one()
    return ListStatsResponse(
        total_domains=total_domains,
        whitelist_count=whitelist_count,
        blacklist_count=blacklist_count,
        manual_count=manual_count,
        llm_count=llm_count
    )
