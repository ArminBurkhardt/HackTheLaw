from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Model strings — confirmed GA as of Jun 2026.
    # gemini-3.1-pro is still preview in europe-west1; fallback = gemini-2.5-pro.
    reasoning_model: str = "gemini-2.5-pro"
    fast_model: str = "gemini-2.5-flash"
    session_prep_model: str = "gemini-3.1-flash-lite"

    google_cloud_project: str | None = None
    google_cloud_location: str = "europe-west1"
    google_api_key: str | None = None

    live_audio_model: str = "models/gemini-3.1-flash-live-preview"
    live_audio_voice: str = "Zephyr"
    live_audio_debug: bool = False

    perplexity_api_key: str | None = None
    allowed_sources_path: str | None = None

    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None

    # text-embedding-004 = 768 dim; bge-m3 = 1024. Both must match the Neo4j vector index.
    embed_model: str = "text-embedding-004"
    embed_dim: int = 768

    # Defaults to fast_model when None — resolved via get_entailment_model()
    entailment_model: str | None = None

    opponent_spot_the_bad_citation: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def get_entailment_model(self) -> str:
        return self.entailment_model or self.fast_model


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
