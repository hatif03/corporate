from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Single source of runtime config. Never read os.environ directly elsewhere."""

    google_cloud_project: str
    google_genai_use_vertexai: bool = True
    vertex_location: str = "us-central1"

    corporate_gemini_model: str = "gemini-2.5-flash"
    corporate_default_org_id: str = "demo"
    corporate_pubsub_topic: str = "agent-bus"
    corporate_backend_url: str = ""
    # Public URL of the standalone A2A server (app/a2a_server.py), once
    # deployed as its own Cloud Run service — see ADR-0004. Empty in local dev.
    corporate_a2a_sales_url: str = ""

    local_dev: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
