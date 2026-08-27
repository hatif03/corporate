from unittest.mock import patch

from shared.custom_skills import with_custom_guidance


def test_with_custom_guidance_returns_input_unchanged_when_no_skills():
    with patch("shared.custom_skills.store.list_agent_custom_skills", return_value=[]):
        assert with_custom_guidance("org-test", "engineering_sre", "base input") == "base input"


def test_with_custom_guidance_prepends_skills():
    skills = [{"title": "Always escalate P1s", "instructions": "Page the on-call immediately for any P1."}]
    with patch("shared.custom_skills.store.list_agent_custom_skills", return_value=skills):
        result = with_custom_guidance("org-test", "engineering_sre", "base input")

    assert result.startswith("Org-specific guidance for this agent:")
    assert "Always escalate P1s" in result
    assert "Page the on-call immediately" in result
    assert result.endswith("base input")


def test_with_custom_guidance_joins_multiple_skills():
    skills = [
        {"title": "A", "instructions": "do A"},
        {"title": "B", "instructions": "do B"},
    ]
    with patch("shared.custom_skills.store.list_agent_custom_skills", return_value=skills):
        result = with_custom_guidance("org-test", "engineering_sre", "base")

    assert "- A: do A" in result
    assert "- B: do B" in result
