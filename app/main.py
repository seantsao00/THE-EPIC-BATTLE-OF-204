from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from .api import auth, domains, lists
from .database import Base, engine
from .dns_proxy import start_dns_proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start DNS proxy on 127.0.0.1:5353
    start_dns_proxy(port=5353)
    print("DNS Proxy started at 127.0.0.1:5353")
    yield

load_dotenv()

app = FastAPI(title="Firewall DNS API", lifespan=lifespan)

# Create DB tables
Base.metadata.create_all(bind=engine)

# Mount routers
app.include_router(auth.router)
app.include_router(domains.router)
app.include_router(lists.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
