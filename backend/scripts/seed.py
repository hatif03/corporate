"""Seeds the demo org with the CEO and every registered department as
Firestore agents, and one Pub/Sub push subscription per agent. Run once
after `gcloud pubsub topics create agent-bus` and Firestore setup (see
/infra/deploy/ and README.md), and again any time a new department is added.

Usage: python scripts/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import pubsub_v1

from app.config import settings
from app.models import Agent
from departments import list_departments
from app.services import store


def seed_agents(org_id: str) -> list[str]:
    agent_ids = ["ceo"]
    store.upsert_agent(
        org_id,
        Agent(id="ceo", name="CEO", department="executive", is_ceo=True, accent_color="lemon"),
    )
    for dept in list_departments():
        store.upsert_agent(
            org_id,
            Agent(id=dept.department_id, name=dept.display_name, department=dept.department_id),
        )
        agent_ids.append(dept.department_id)
    return agent_ids


def create_push_subscriptions(org_id: str, agent_ids: list[str]) -> None:
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = subscriber.topic_path(settings.google_cloud_project, settings.corporate_pubsub_topic)
    for agent_id in agent_ids:
        sub_path = subscriber.subscription_path(settings.google_cloud_project, f"sub-{org_id}-{agent_id}")
        push_config = pubsub_v1.types.PushConfig(
            push_endpoint=f"{settings.corporate_backend_url}/internal/agent-turn/{agent_id}",
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
        except Exception as exc:  # already-exists is fine on re-run
            print(f"skipped {sub_path}: {exc}")


if __name__ == "__main__":
    org_id = settings.corporate_default_org_id
    agent_ids = seed_agents(org_id)
    print(f"seeded agents for org '{org_id}': {agent_ids}")
    if not settings.local_dev:
        create_push_subscriptions(org_id, agent_ids)
