import enum
from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from .database import Base

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

class DomainLog(Base):
    __tablename__ = "domain_logs"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), index=True)
    status = Column(Enum(DomainStatus), default=DomainStatus.reviewed, nullable=False)
    timestamp = Column(DateTime, default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True)
    hashed_password = Column(String(128))

class DomainList(Base):
    __tablename__ = "domain_lists"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, index=True)
    list_type = Column(Enum(ListType), index=True, nullable=False)
    source = Column(Enum(ListSource), nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
