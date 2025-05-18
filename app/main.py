import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from .api import auth, domains, lists
from .database import Base, engine
from .dns_proxy import start_dns_proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    dns_port = int(os.environ.get("DNS_PORT", 5353))
    start_dns_proxy(port=dns_port)
    print(f"DNS Proxy started at 127.0.0.1:{dns_port}")
    yield

load_dotenv()

app = FastAPI(title="Firewall DNS API", lifespan=lifespan)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(domains.router)
app.include_router(lists.router)


if __name__ == "__main__":
    api_port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=api_port, reload=True)
