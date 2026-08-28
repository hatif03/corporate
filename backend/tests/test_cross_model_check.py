"""Runtime cross-model hallucination checker (shared/cross_model_check.py,
ADR-0019) — the Gemma-backed AspectChecker plugged into vote_aspects
(shared/verification.py). Covers both the agree/disagree paths and the
model-call-failure path, matching this project's convention of testing
failure paths, not just happy ones."""

from unittest.mock import AsyncMock, MagicMock, patch

from shared.cross_model_check import make_gemma_checker


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=MagicMock(text=response_text))
    return client


async def test_gemma_checker_passes_when_model_agrees():
    checker = make_gemma_checker("gemma_cross_check", lambda claim: "a plausible claim")
    with patch("shared.cross_model_check.genai.Client", return_value=_mock_client("Yes")):
        vote = await checker({})

    assert vote.aspect == "gemma_cross_check"
    assert vote.passed is True


async def test_gemma_checker_fails_when_model_disagrees():
    checker = make_gemma_checker("gemma_cross_check", lambda claim: "a dubious claim")
    with patch("shared.cross_model_check.genai.Client", return_value=_mock_client("No, this looks fabricated.")):
        vote = await checker({})

    assert vote.passed is False


async def test_gemma_checker_treats_call_failure_as_a_no_not_a_crash():
    checker = make_gemma_checker("gemma_cross_check", lambda claim: "anything")
    with patch("shared.cross_model_check.genai.Client", side_effect=RuntimeError("quota exceeded")):
        vote = await checker({})

    assert vote.passed is False
    assert "quota exceeded" in vote.reason


async def test_describe_fn_receives_the_real_claim_dict():
    seen = {}

    def describe(claim: dict) -> str:
        seen["claim"] = claim
        return "described"

    checker = make_gemma_checker("x", describe)
    with patch("shared.cross_model_check.genai.Client", return_value=_mock_client("yes")):
        await checker({"invoice": {"vendor": "Acme"}})

    assert seen["claim"] == {"invoice": {"vendor": "Acme"}}
