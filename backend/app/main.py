from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api import audit, integrations, internal, memory, org, triggers, workers
from app.config import settings
from app.services.auth import require_org_member


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

# /internal/* is authenticated separately (Pub/Sub push OIDC / Cloud
# Scheduler IAM, see app/api/internal.py) — never wired with
# require_org_member, which expects an end-user Firebase ID token.
app.include_router(internal.router)
app.include_router(triggers.internal_router)

# Every /api/org/{org_id}/* router requires the caller to be an
# authenticated, verified member of that org — wired once here at the
# router level so a new endpoint added to any of these routers can't
# accidentally ship without auth. See app/services/auth.py.
_org_scoped_dependency = [Depends(require_org_member)]
app.include_router(org.router, dependencies=_org_scoped_dependency)
app.include_router(audit.router, dependencies=_org_scoped_dependency)
app.include_router(triggers.router, dependencies=_org_scoped_dependency)
app.include_router(workers.router, dependencies=_org_scoped_dependency)
app.include_router(memory.router, dependencies=_org_scoped_dependency)
app.include_router(integrations.router, dependencies=_org_scoped_dependency)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "project": settings.google_cloud_project}
