"""Firestore-backed ADK session service.

Cloud Run instances are ephemeral and this project delivers one Pub/Sub
message per agent turn, potentially to a different instance each time —
InMemorySessionService would silently lose context. Sessions are persisted at
orgs/{org_id}/agent_sessions/{agent_id} (session_id == agent_id, user_id ==
org_id, app_name == "corporate" for every session in this project).

Events are stored as a single array field on the session doc, not a
subcollection like agents/{id}/trace. To keep that array from ever hitting
Firestore's 1MiB document cap, _persist() runs it through
app/services/compaction.py before every write — see that module's docstring
(adapted from opencode's compaction pattern, MIT, docs/adr/0015). If
compaction alone stops being enough at real scale, the next upgrade is
moving events to an agent_sessions/{agentId}/events/{seq} subcollection the
same way trace already works, and updating get_session()/append_event() to
read/write it instead — noted here, not built now.
"""

from __future__ import annotations

from typing import Any, Optional

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session

from app.services import compaction, store
from app.services.firestore_client import org_collection, org_doc


def _uid_to_agent_id(user_id: str) -> str:
    # In this project user_id is always the org id and session_id is always
    # the agent id — see the module docstring. Kept as a named seam in case
    # that assumption ever needs to change.
    return user_id


class FirestoreSessionService(BaseSessionService):
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        org_id = user_id
        if not session_id:
            raise ValueError("FirestoreSessionService requires an explicit session_id (the agent id)")
        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {},
            events=[],
        )
        await self._persist(org_id, session)
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        org_id = user_id
        snap = org_doc(org_id, "agent_sessions", session_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict()
        events = [Event.model_validate(e) for e in data.get("events", [])]
        if config:
            if config.num_recent_events is not None:
                events = events[-config.num_recent_events :] if config.num_recent_events else []
            if config.after_timestamp:
                events = [e for e in events if e.timestamp >= config.after_timestamp]
        return Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=data.get("state", {}),
            events=events,
        )

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        if user_id is None:
            raise NotImplementedError(
                "FirestoreSessionService.list_sessions requires user_id (org_id) — "
                "listing across all orgs is not supported."
            )
        org_id = user_id
        sessions = []
        for snap in org_collection(org_id, "agent_sessions").stream():
            data = snap.to_dict()
            sessions.append(
                Session(app_name=app_name, user_id=user_id, id=snap.id, state=data.get("state", {}), events=[])
            )
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        org_doc(user_id, "agent_sessions", session_id).delete()

    async def append_event(self, session: Session, event: Event) -> Event:
        event = await super().append_event(session, event)
        await self._persist(session.user_id, session)
        return event

    async def _persist(self, org_id: str, session: Session) -> None:
        if compaction.should_compact(session.events):
            try:
                session.events = await compaction.compact_events(org_id, session.events)
            except Exception as exc:  # noqa: BLE001 - compaction must never break a real turn
                store.log_activity(org_id, session.id, "compaction-failed", str(exc))
        org_doc(org_id, "agent_sessions", session.id).set(
            {
                "state": session.state,
                "events": [e.model_dump(mode="json") for e in session.events],
            }
        )
