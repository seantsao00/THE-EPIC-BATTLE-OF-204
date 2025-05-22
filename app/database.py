from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .settings import settings

SQLALCHEMY_DATABASE_URL = settings.sqlalchemy_database_url

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SQLModel.metadata.create_all(bind=engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
