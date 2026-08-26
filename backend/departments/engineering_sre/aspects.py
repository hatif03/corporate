"""Aspect checkers this department contributes to the shared verifier
(shared/verification.py's vote_aspects), same pattern as
finance_audit/aspects.py. Each receives {"triage": ..., "cascade": ...} —
the two structured classifications built in agents.py's finalize step."""

from __future__ import annotations

from shared.verification import AspectVote

_VALID_SEVERITIES = {"P1", "P2", "P3", "P4"}
_HIGH_SEVERITIES = {"P1", "P2"}


async def schema_consistency(claim: dict) -> AspectVote:
    triage = claim["triage"]
    missing = [f for f in ("severity", "affected_systems", "summary") if not triage.get(f)]
    valid_severity = triage.get("severity") in _VALID_SEVERITIES
    passed = not missing and valid_severity
    reason = "complete and valid" if passed else f"missing={missing} severity={triage.get('severity')}"
    return AspectVote("schema_consistency", passed=passed, reason=reason)


async def severity_cascade_consistency(claim: dict) -> AspectVote:
    triage, cascade = claim["triage"], claim["cascade"]
    suspicious = (
        triage.get("severity") in _HIGH_SEVERITIES
        and cascade.get("cascade_risk") == "low"
        and len(triage.get("affected_systems", [])) > 2
    )
    reason = (
        "plausible"
        if not suspicious
        else "high severity with several affected systems but cascade risk marked low"
    )
    return AspectVote("severity_cascade_consistency", passed=not suspicious, reason=reason)


ASPECTS = {
    "schema_consistency": schema_consistency,
    "severity_cascade_consistency": severity_cascade_consistency,
}
