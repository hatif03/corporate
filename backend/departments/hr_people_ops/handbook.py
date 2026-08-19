"""A small embedded policy corpus, used as the handbook_qa stage's grounding
context. ponytail: this is a hardcoded string, not a real document store
(Notion/Confluence, per docs/system_prompt.md's Integrations phasing) —
fine for a demo with one static handbook; swap for a real synced corpus once
that integration exists, without changing agents.py's call shape."""

HR_HANDBOOK = """\
Paid time off: full-time employees accrue 15 days of PTO per year, prorated
by start date. PTO requests must be submitted at least 5 business days in
advance and require manager approval.

Remote work: employees may work remotely up to 3 days per week by default;
fully remote arrangements require VP-level sign-off.

Onboarding: every new hire gets a laptop, a buddy assigned in their first
week, and completes security/compliance training within their first 10 days.

Parental leave: 16 weeks paid leave for the primary caregiver, 8 weeks for
the secondary caregiver, available after 90 days of employment.

Expense reimbursement: submit receipts within 30 days of purchase; anything
over $500 requires manager pre-approval before purchase, not after.
"""
