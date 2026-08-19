from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import audit, internal, org
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.local_dev:
        from app.services.dispatch import handle_agent_turn
        from app.services.pubsub_local import drain_local

        async def handler(org_id: str, message) -> None:
            await handle_agent_turn(org_id, message.to, message)

        task = asyncio.create_task(drain_local(handler))
        yield
        task.cancel()
    else:
        yield


app = FastAPI(title="Corporate backend", lifespan=lifespan)

app.include_router(internal.router)
app.include_router(org.router)
app.include_router(audit.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "project": settings.google_cloud_project}
