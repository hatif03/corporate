from unittest.mock import MagicMock, patch

from app.services.memory_search import search_memory


def _agent(agent_id: str):
    fake = MagicMock()
    fake.id = agent_id
    return fake


def test_search_ranks_by_similarity_across_agents():
    memory_by_agent = {
        "finance_audit": [
            {"id": "m1", "text": "invoice fraud pattern noted", "embedding": [1.0, 0.0, 0.0]},
        ],
        "engineering_sre": [
            {"id": "m2", "text": "auth-service outage last week", "embedding": [0.0, 1.0, 0.0]},
        ],
    }

    def fake_list_memory(org_id, agent_id, limit_count=200):
        return memory_by_agent.get(agent_id, [])

    with (
        patch("app.services.memory_search.embed_text", return_value=[0.9, 0.1, 0.0]),
        patch("app.services.memory_search.store.list_agents", return_value=[_agent("finance_audit"), _agent("engineering_sre")]),
        patch("app.services.memory_search.store.list_memory", side_effect=fake_list_memory),
    ):
        hits = search_memory("org-test", "any fraud signals?", top_k=5)

    assert len(hits) == 2
    assert hits[0].agent_id == "finance_audit"  # closer to the query vector
    assert hits[0].score > hits[1].score


def test_search_can_scope_to_a_single_agent():
    with (
        patch("app.services.memory_search.embed_text", return_value=[1.0, 0.0]),
        patch(
            "app.services.memory_search.store.list_memory",
            return_value=[{"id": "m1", "text": "note", "embedding": [1.0, 0.0]}],
        ),
        patch("app.services.memory_search.store.list_agents") as mock_list_agents,
    ):
        hits = search_memory("org-test", "note", agent_id="finance_audit")

    assert not mock_list_agents.called  # scoped search shouldn't need the full roster
    assert len(hits) == 1
    assert hits[0].agent_id == "finance_audit"


def test_entries_without_embeddings_are_skipped():
    with (
        patch("app.services.memory_search.embed_text", return_value=[1.0, 0.0]),
        patch(
            "app.services.memory_search.store.list_memory",
            return_value=[{"id": "m1", "text": "no embedding here", "embedding": None}],
        ),
    ):
        hits = search_memory("org-test", "note", agent_id="finance_audit")

    assert hits == []
