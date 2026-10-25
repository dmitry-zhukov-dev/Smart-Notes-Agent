
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash"

    langfuse_secret_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    langfuse_tracing_enabled: bool = False
    langfuse_mask_data: bool = False


settings = Settings()
