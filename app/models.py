import enum
from datetime import datetime

from sqlmodel import Field, SQLModel


class DomainStatus(str, enum.Enum):
    allowed = "allowed"
    blocked = "blocked"
    reviewed = "reviewed"


class ListType(str, enum.Enum):
    whitelist = "whitelist"
    blacklist = "blacklist"


class ListSource(str, enum.Enum):
    manual = "manual"
    llm = "llm"


class DomainLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    domain: str = Field(index=True, max_length=255)
    status: DomainStatus = Field(default=DomainStatus.reviewed)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=64)
    hashed_password: str = Field(max_length=128)


class DomainList(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    domain: str = Field(index=True, unique=True, max_length=255)
    list_type: ListType = Field(index=True)
    source: ListSource
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
