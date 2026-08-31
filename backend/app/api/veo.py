""""Internal polling endpoint for pending Veo video-generation operations
(ADR-0019) — the completion half of departments/marketing_comms/agents.py's
fire-and-forget kickoff. Same shape as app/api/triggers.py's Cloud-Scheduler-
driven internal fire endpoint: a recurring Cloud Scheduler job (created
once, manually, same as any schedule-type trigger) hits this every minute
or two; not wired to any org-scoped auth since Cloud Scheduler carries an
OIDC token instead (require_internal_oidc, same as every other /internal/*
route).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services import store
from app.services.storage_client import sign_existing_gcs_uri
from app.services.veo_client import check_video_generation

internal_router = APIRouter(prefix="/internal/veo/{org_id}", tags=["veo-internal"])


@internal_router.post("/poll")
async def poll_pending_operations(org_id: str) -> dict:
    checked = 0
    completed = 0
    failed = 0

    for op in store.list_veo_operations(org_id):
        checked += 1
        task_id, operation_name = op["taskId"], op["operationName"]
        try:
            video_uri = await check_video_generation(operation_name)
        except Exception as exc:  # noqa: BLE001 - one bad operation must never block checking the rest
            failed += 1
            store.log_activity(org_id, "marketing_comms", "veo-generation-failed", f"task {task_id}: {exc}")
            store.delete_veo_operation(org_id, task_id)
            continue

        if video_uri is None:
            continue  # still running, check again next poll

        task = store.get_task(org_id, task_id)
        if task is not None:
            # video_uri is a gs:// URI (only Vertex/gcloud tooling can
            # dereference that) — sign it before a browser <video> tag ever
            # sees it. Reproduced live: without this the player rendered a
            # blank box with an unplayable src, and videoGenerating stayed
            # true forever since nothing ever cleared it.
            playable_url = sign_existing_gcs_uri(video_uri)
            store.update_task(
                org_id, task_id, result={**(task.result or {}), "videoUrl": playable_url, "videoGenerating": False}
            )
        completed += 1
        store.delete_veo_operation(org_id, task_id)

    return {"checked": checked, "completed": completed, "failed": failed}
