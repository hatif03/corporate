"""Embedded support KB — same "static corpus now, real integration later"
pattern as hr_people_ops/handbook.py. Keyed by intent so kb_retriever can
pull the right slice without a real vector index."""

KNOWLEDGE_BASE: dict[str, str] = {
    "billing": (
        "Refunds are issued for cancellations requested within 14 days of purchase. "
        "Subscription downgrades take effect at the start of the next billing cycle, not immediately. "
        "Failed payments retry automatically 3 times over 7 days before a subscription is suspended."
    ),
    "technical": (
        "The API rate limit is 100 requests per minute per API key. "
        "Webhook deliveries retry with exponential backoff for up to 24 hours on failure. "
        "Data exports are available in CSV and JSON, generated asynchronously and emailed when ready."
    ),
    "account": (
        "Password resets are self-service via the login page and expire after 1 hour. "
        "Account deletion requests are processed within 30 days and are not reversible after that window. "
        "Team seats can be added or removed by an account admin at any time."
    ),
}

DEFAULT_KB_NOTE = "No specific knowledge base article matches this intent."
