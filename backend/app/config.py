from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Single source of runtime config. Never read os.environ directly elsewhere."""

    google_cloud_project: str
    google_genai_use_vertexai: bool = True
    vertex_location: str = "us-central1"

    corporate_gemini_model: str = "gemini-2.5-flash"
    # Higher-capability tier for tasks the CEO marks model_tier="pro" when
    # calling create_task — see ADR-0013 and app/adk_agents/factory.py's
    # build_tiered_stage_agents().
    corporate_gemini_model_pro: str = "gemini-2.5-pro"
    corporate_default_org_id: str = "demo"
    corporate_pubsub_topic: str = "agent-bus"
    corporate_backend_url: str = ""
    # Public URL of the standalone A2A server (app/a2a_server.py), once
    # deployed as its own Cloud Run service — see ADR-0004. Empty in local dev.
    corporate_a2a_sales_url: str = ""
    # GCS bucket for vision attachments (app/services/storage_client.py) — no
    # gs:// prefix, just the bucket name. See ADR-0013.
    corporate_attachments_bucket: str = ""

    # Circuit breaker on raw Gemini call volume/spend — the hop-cap in
    # pubsub_client.py bounds message ping-pong, not this. See ADR-0012.
    # This is now only the ops-level emergency-valve fallback used when an
    # org hasn't set its own orgs/{orgId}/settings/config.dailyGeminiCallLimit
    # (see app/services/store.py's get_org_settings) — high enough to be
    # invisible for any realistic demo, low enough to still stop a genuine
    # runaway loop. See ADR-0013.
    corporate_daily_gemini_call_limit: int = 5000

    local_dev: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
