"""Redact-before-LLM PII handling. Any department ingesting externally- or
user-sourced text (Slack messages, pasted transcripts, uploaded documents)
runs it through redact() before the content reaches Gemini.

ponytail: this is regex-based pattern matching, not a real NLP-backed PII
detector (e.g. Microsoft Presidio + spaCy NER, which catches names/addresses/
context-dependent PII that no regex can). Regex catches the
structurally-identifiable categories below reliably; it will miss anything
that doesn't have a fixed shape. Upgrade path: swap the REDACTORS list here
for a Presidio AnalyzerEngine + AnonymizerEngine pipeline once a department
actually needs name/address-level redaction — the redact() call signature
below is designed not to need to change if that swap happens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_AWS_KEY = re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")

REDACTORS: dict[str, re.Pattern] = {
    "EMAIL": _EMAIL,
    "PHONE": _PHONE,
    "SSN": _SSN,
    "CREDIT_CARD": _CREDIT_CARD,
    "AWS_KEY": _AWS_KEY,
}


@dataclass
class RedactionResult:
    redacted_text: str
    found: dict[str, int] = field(default_factory=dict)

    @property
    def had_pii(self) -> bool:
        return bool(self.found)


def redact(text: str) -> RedactionResult:
    """Replace every matched pattern with a `[REDACTED:<category>]` token and
    report what categories fired (never the matched values themselves —
    callers must not log or persist RedactionResult.found values, only the
    category names and counts)."""
    found: dict[str, int] = {}
    redacted = text
    for category, pattern in REDACTORS.items():
        redacted, count = pattern.subn(f"[REDACTED:{category}]", redacted)
        if count:
            found[category] = count
    return RedactionResult(redacted_text=redacted, found=found)
