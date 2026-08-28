from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import access_requests, agents, audit, breakroom, integrations, internal, knowledge_base, memory, oauth, org, triggers, veo, voice, workers
from app.config import settings
from app.services import store
from app.services.auth import require_internal_oidc, require_org_member

logger = logging.getLogger(__name__)


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

# The frontend (Firebase Hosting) and this backend (Cloud Run) are different
# origins, so the browser needs an explicit CORS allow — auth itself is
# still enforced by require_org_member (Bearer token, not cookies, so no
# allow_credentials needed here).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://{settings.google_cloud_project}.web.app",
        f"https://{settings.google_cloud_project}.firebaseapp.com",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# /internal/* is authenticated separately (Pub/Sub push / Cloud Scheduler
# OIDC tokens via require_internal_oidc, see app/services/auth.py) — never
# wired with require_org_member, which expects an end-user Firebase ID token.
# internal.router carries its own dependency already; triggers.internal_router
# doesn't, so it's added here.
app.include_router(internal.router)
app.include_router(triggers.internal_router, dependencies=[Depends(require_internal_oidc)])
app.include_router(veo.internal_router, dependencies=[Depends(require_internal_oidc)])

# Every /api/org/{org_id}/* router requires the caller to be an
# authenticated, verified member of that org — wired once here at the
# router level so a new endpoint added to any of these routers can't
# accidentally ship without auth. See app/services/auth.py.
_org_scoped_dependency = [Depends(require_org_member)]
app.include_router(org.router, dependencies=_org_scoped_dependency)
app.include_router(agents.router, dependencies=_org_scoped_dependency)
app.include_router(audit.router, dependencies=_org_scoped_dependency)
app.include_router(triggers.router, dependencies=_org_scoped_dependency)
app.include_router(workers.router, dependencies=_org_scoped_dependency)
app.include_router(memory.router, dependencies=_org_scoped_dependency)
app.include_router(integrations.router, dependencies=_org_scoped_dependency)
app.include_router(access_requests.router, dependencies=_org_scoped_dependency)
app.include_router(knowledge_base.router, dependencies=_org_scoped_dependency)
app.include_router(breakroom.router, dependencies=_org_scoped_dependency)

# Not wired with _org_scoped_dependency: browsers can't set custom headers
# on a WebSocket handshake, so require_org_member's Authorization-header
# check would always fail here. voice.py authenticates itself from a
# query-param token instead — see that module's docstring.
app.include_router(voice.router)

# Not wired with _org_scoped_dependency either: /oauth/start is a plain
# browser navigation (same header limitation as the WebSocket above,
# authenticates itself via ?token=), and /oauth/{kind}/callback is called
# directly by the OAuth provider, which carries no Firebase token at all —
# its own signed `state` param is the real access control. See
# app/api/oauth.py's module docstring.
app.include_router(oauth.router)


# Catches anything NOT already raised as an HTTPException — a raw Firestore/
# Secret-Manager/httpx error in a route with no try/except of its own
# (confirmed real gap: only department task processing gets this via
# @audited_task, backend/departments/base.py; every other route had nothing,
# falling through to Starlette's bare default 500). One shared fix here
# instead of hand-wrapping every route — same root-cause-not-symptom
# reasoning @audited_task already applies at the task layer. FastAPI's own
# HTTPException handler is registered separately and takes priority for
# anything that already raises one deliberately, so this only ever fires
# for genuinely unhandled failures.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    org_id = request.path_params.get("org_id")
    logger.exception("unhandled exception on %s %s (org=%s)", request.method, request.url.path, org_id)
    if org_id:
        try:
            store.log_activity(org_id, "backend", "unhandled-exception", f"{request.method} {request.url.path}: {exc}")
        except Exception:  # noqa: BLE001 - logging the original failure must never itself crash the handler
            pass
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


# Not /healthz: on the shared *.run.app domain, Google's own front end
# intercepts that exact path for its own synthetic monitoring before the
# request ever reaches this container — confirmed live (every other path,
# including a nonexistent one, correctly reaches FastAPI).
@app.get("/api/healthz")
async def healthz() -> dict:
    try:
        store.get_org_settings(settings.corporate_default_org_id)
        firestore_status = "ok"
    except Exception as exc:  # noqa: BLE001 - a health check reports failure, it doesn't propagate one
        firestore_status = f"error: {exc}"
    return {"status": "ok" if firestore_status == "ok" else "degraded", "project": settings.google_cloud_project, "firestore": firestore_status}
