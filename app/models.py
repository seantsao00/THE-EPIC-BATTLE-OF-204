from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from .database import Base


class DomainLog(Base):
    __tablename__ = "domain_logs"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=False, index=True)
    status = Column(String)  # allowed, blocked, review
    first_seen = Column(DateTime, default=func.now())
    last_seen = Column(DateTime, default=func.now(), onupdate=func.now())
    count = Column(Integer, default=1)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class DomainList(Base):
    __tablename__ = "domain_lists"
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True)
    list_type = Column(String)  # 'whitelist' or 'blacklist'
