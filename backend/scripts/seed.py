"""Seeds the demo org with the CEO and every registered department as
Firestore agents, one Pub/Sub push subscription per agent, and (optionally)
an owner membership so someone can actually pass the auth check in
app/services/auth.py once this is deployed. Run once after
`gcloud pubsub topics create agent-bus` and Firestore setup (see
/infra/deploy/ and README.md), and again any time a new department is added.

Usage:
    python scripts/seed.py
    python scripts/seed.py --owner-uid <firebase-uid>   # also grants org ownership
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

from app.config import settings
from app.models import Agent, Trigger, TriggerType
from app.services import store
from departments import list_departments
from shared.personas import PERSONA_VOICE


# Personas named by purpose, not by person — an agent's name IS its job
# title, so a non-technical user never has to wonder who "Wren Castellano"
# is. `character` picks a stable Kenney sprite variant
# (frontend/src/scene/office/tileset.ts's variantForCharacter) so agents
# sharing a department zone (e.g. ceo + executive) render as visibly
# distinct people, not identical hash-based twins.
PERSONAS: dict[str, dict[str, str]] = {
    "ceo": {"name": "CEO", "description": "Sets direction and decomposes every goal into department work.", "character": "char_0"},
    "executive": {"name": "Chief of Staff", "description": "Turns every department's board into one weekly digest.", "character": "char_1"},
    "finance_audit": {"name": "Finance & Audit Lead", "description": "Catches the invoice that doesn't add up.", "character": "char_2"},
    "engineering_sre": {"name": "Engineering & SRE Lead", "description": "Keeps the lights on and the pager quiet.", "character": "char_3"},
    "legal_risk": {"name": "Legal & Risk Lead", "description": "Reads the fine print first.", "character": "char_4"},
    "hr_people_ops": {"name": "HR & People Ops Lead", "description": "Knows everyone's start date.", "character": "char_5"},
    "customer_support": {"name": "Customer Support Lead", "description": "Turns angry tickets into calm ones.", "character": "char_6"},
    "marketing_comms": {"name": "Marketing & Comms Lead", "description": "Writes the launch email people actually read.", "character": "char_7"},
    "product_analytics": {"name": "Product & Analytics Lead", "description": "Has a dashboard for the dashboard.", "character": "char_0"},
    "sales_crm": {"name": "Sales & CRM Lead", "description": "Never forgets a follow-up.", "character": "char_1"},
}


def seed_agents(org_id: str) -> list[str]:
    agent_ids = ["ceo"]
    ceo_persona = PERSONAS["ceo"]
    store.upsert_agent(
        org_id,
        Agent(
            id="ceo",
            name=ceo_persona["name"],
            description=ceo_persona["description"],
            character=ceo_persona["character"],
            voice=PERSONA_VOICE.get("ceo"),
            department="executive",
            is_ceo=True,
            accent_color="lemon",
        ),
    )
    for dept in list_departments():
        persona = PERSONAS.get(dept.department_id, {})
        store.upsert_agent(
            org_id,
            Agent(
                id=dept.department_id,
                name=persona.get("name", dept.display_name),
                description=persona.get("description", ""),
                character=persona.get("character", "default"),
                voice=PERSONA_VOICE.get(dept.department_id),
                department=dept.department_id,
            ),
        )
        agent_ids.append(dept.department_id)
    return agent_ids


# Proactive self-check + periodic memory curation — adapted from OpenClaw's
# background heartbeats/independent task assessment and Hermes-agent's
# agent-curated memory with periodic nudges (see docs/adr/0019-...), built
# natively on the Trigger model that already exists (app/models/trigger.py)
# rather than any new subsystem. Scoped to the CEO for this pass — the CEO
# already has list_agents_tool/list_tasks_tool/create_task and (as of this
# change) memory tools too, so it can act on what it finds; extending this
# to per-department autonomous turns would need dispatch.py to handle a
# trigger-fired department turn with no backing Task, which is real
# follow-up work, not done here.
#
# Fixed ids make this idempotent (store.create_trigger upserts by id) — safe
# to re-run on every deploy. Firing these on schedule still needs a one-time
# manual `gcloud scheduler jobs create http` per trigger targeting
# /internal/triggers/{org_id}/{trigger_id}/fire — same as any other
# schedule-type trigger (see app/api/triggers.py's module docstring).
DEFAULT_TRIGGERS: list[Trigger] = [
    Trigger(
        id="trig-ceo-self-check",
        name="CEO self-check",
        type=TriggerType.SCHEDULE,
        target_agent="ceo",
        payload_template=(
            "Autonomous self-check: use list_agents_tool and list_tasks_tool to review the company's current "
            "state. If anything looks stalled, blocked, or worth escalating, take action (create_task, "
            "send_message) or note it via write_board. If nothing needs attention, do nothing — this is a "
            "routine check, not a request for busywork."
        ),
        cron="*/30 * * * *",
    ),
    Trigger(
        id="trig-ceo-memory-curation",
        name="CEO memory curation",
        type=TriggerType.SCHEDULE,
        target_agent="ceo",
        payload_template=(
            "Memory curation: use read_memory to review your own long-term notes. If any are stale, redundant, "
            "or superseded by a more recent one, use write_memory to save a single consolidated replacement note "
            "— you can't delete old entries, so don't bother flagging that, just add a better one going forward. "
            "If your memory is already small and clean, do nothing."
        ),
        cron="0 3 * * *",
    ),
]


def seed_default_triggers(org_id: str) -> None:
    for trigger in DEFAULT_TRIGGERS:
        store.create_trigger(org_id, trigger)


def create_push_subscriptions(org_id: str, agent_ids: list[str]) -> None:
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = subscriber.topic_path(settings.google_cloud_project, settings.corporate_pubsub_topic)
    # Pub/Sub must attach a verifiable OIDC token to each push so
    # require_internal_oidc (app/services/auth.py) can check it — the
    # backend is deployed --allow-unauthenticated, so this token is the
    # actual access control on /internal/*, not Cloud Run's own IAM gate.
    push_sa = f"corporate-backend-sa@{settings.google_cloud_project}.iam.gserviceaccount.com"
    for agent_id in agent_ids:
        sub_path = subscriber.subscription_path(settings.google_cloud_project, f"sub-{org_id}-{agent_id}")
        push_endpoint = f"{settings.corporate_backend_url}/internal/agent-turn/{agent_id}"
        push_config = pubsub_v1.types.PushConfig(
            push_endpoint=push_endpoint,
            oidc_token=pubsub_v1.types.PushConfig.OidcToken(service_account_email=push_sa, audience=push_endpoint),
        )
        try:
            subscriber.create_subscription(
                request={
                    "name": sub_path,
                    "topic": topic_path,
                    "push_config": push_config,
                    "filter": f'attributes.orgId="{org_id}" AND (attributes.to="{agent_id}" OR attributes.to="broadcast")',
                }
            )
            print(f"created subscription {sub_path}")
        except AlreadyExists:
            subscriber.update_subscription(
                request={
                    "subscription": {"name": sub_path, "push_config": push_config},
                    "update_mask": {"paths": ["push_config"]},
                }
            )
            print(f"subscription {sub_path} already existed, updated push_config")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-uid", help="Firebase Auth uid to grant 'owner' role in the demo org")
    args = parser.parse_args()

    org_id = settings.corporate_default_org_id
    agent_ids = seed_agents(org_id)
    print(f"seeded agents for org '{org_id}': {agent_ids}")

    seed_default_triggers(org_id)
    print(f"seeded default triggers for org '{org_id}': {[t.id for t in DEFAULT_TRIGGERS]}")
    print("  (each still needs a one-time `gcloud scheduler jobs create http` — see app/api/triggers.py)")

    if args.owner_uid:
        store.add_member(org_id, args.owner_uid, role="owner")
        print(f"granted owner role to uid '{args.owner_uid}' in org '{org_id}'")

    if not settings.local_dev:
        create_push_subscriptions(org_id, agent_ids)
