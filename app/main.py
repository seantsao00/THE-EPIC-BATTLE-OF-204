import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, domain_logs, lists
from .database import Base, engine
from .dns_proxy import start_dns_proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    dns_port = int(os.environ.get("DNS_PORT", 5353))
    dns_ip = os.environ.get("DNS_IP", "127.0.0.1")
    start_dns_proxy(ip=dns_ip, port=dns_port)
    print(f"DNS Proxy started at {dns_ip}:{dns_port}")
    yield

load_dotenv()

app = FastAPI(title="Firewall DNS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(domain_logs.router)
app.include_router(lists.router)


if __name__ == "__main__":
    api_port = int(os.environ.get("API_PORT", 8000))
    api_ip = os.environ.get("API_IP", "127.0.0.1")
    uvicorn.run("app.main:app", host=api_ip, port=api_port, reload=True)
