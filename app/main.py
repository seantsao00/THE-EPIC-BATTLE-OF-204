from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from .api import auth, domain_logs, lists
from .database import engine
from .dns_proxy import start_dns_proxy
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    dns_port = settings.dns_port
    dns_ip = settings.dns_ip
    start_dns_proxy(ip=dns_ip, port=dns_port)
    print(f"DNS Proxy started at {dns_ip}:{dns_port}")
    yield

app = FastAPI(title="Firewall DNS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SQLModel.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(domain_logs.router)
app.include_router(lists.router)


if __name__ == "__main__":
    api_port = settings.api_port
    api_ip = settings.api_ip
    uvicorn.run("app.main:app", host=api_ip, port=api_port, reload=True)
