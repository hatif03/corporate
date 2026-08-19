import pytest

from shared.verification import AspectVote, ground_quote, vote_aspects


def test_ground_quote_exact_match():
    source = "The invoice total is $4,200.00 due on March 3rd."
    assert ground_quote("$4,200.00", source) == "$4,200.00"


def test_ground_quote_fuzzy_match():
    source = "The invoice total is $4,200.00 due on March 3rd."
    # near-verbatim (one character off) should still ground via the fuzzy fallback
    result = ground_quote("$4,200.0O", source)
    assert result is not None


def test_ground_quote_ungroundable_claim_is_dropped():
    source = "The invoice total is $4,200.00 due on March 3rd."
    assert ground_quote("the vendor offered a 50% kickback", source) is None


async def test_vote_aspects_passes_on_majority_agreement():
    async def passer(_claim):
        return AspectVote("a", passed=True)

    async def failer(_claim):
        return AspectVote("b", passed=False)

    result = await vote_aspects({}, {"a": passer, "b": passer, "c": failer})
    assert result.verified is True
    assert result.retried is False


async def test_vote_aspects_fails_after_retry_when_no_agreement():
    async def failer(_claim):
        return AspectVote("x", passed=False)

    result = await vote_aspects({}, {"a": failer, "b": failer})
    assert result.verified is False
    assert result.retried is True


async def test_vote_aspects_requires_at_least_one_checker():
    with pytest.raises(ValueError):
        await vote_aspects({}, {})
