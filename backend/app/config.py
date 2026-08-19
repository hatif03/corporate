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

    local_dev: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
