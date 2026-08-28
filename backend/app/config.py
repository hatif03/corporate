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
    # Independent second model for runtime cross-model hallucination checking
    # (shared/cross_model_check.py, ADR-0019) — fully-managed/serverless on
    # Vertex AI MaaS, same project/location/ADC as everything else, no
    # self-hosted GPU endpoint needed. Deliberately a different model
    # family, not another Gemini tier — the point is an independent judge.
    corporate_gemma_model: str = "gemma-3-27b-it"

    # Break-room ambient music (app/services/lyria_client.py, ADR-0019) — no
    # Python SDK method for Lyria yet (confirmed: google-genai's Models
    # exposes generate_images/generate_videos but no music method), so this
    # calls the raw Vertex AI predict REST endpoint directly. Reconfirm this
    # id against Model Garden at deploy time — same drift risk
    # app/api/voice.py's own VOICE_MODEL constant already documents.
    corporate_lyria_model: str = "lyria-002"

    # Marketing promo-video generation (app/services/veo_client.py, ADR-0019)
    # — reconfirm against Model Garden at deploy time, same drift risk noted
    # for corporate_gemma_model/corporate_lyria_model above.
    corporate_veo_model: str = "veo-3.1-generate-001"
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

    # OAuth "Connect with X" client IDs — public, safe as plain config.
    # Client SECRETS are never here: they're resolved from Secret Manager at
    # request time (app/services/oauth_providers.py), same pattern as every
    # other third-party credential in this app. Each requires a one-time
    # manual app registration in that provider's own developer console —
    # see docs/adr/0018-oauth-connect-flow.md.
    slack_oauth_client_id: str = ""
    github_oauth_client_id: str = ""
    notion_oauth_client_id: str = ""
    # HMAC key signing the OAuth `state` param (CSRF protection) — required
    # for /api/org/{org_id}/integrations/{kind}/oauth/start to work at all;
    # a real secret, not the empty default, must be set before OAuth connect
    # is usable. Plain env var is fine here (not a third-party credential,
    # just a locally-generated signing key with no external value).
    oauth_state_secret: str = ""

    local_dev: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
