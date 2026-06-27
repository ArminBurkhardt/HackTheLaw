import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    runner_backend: str = "adk"
    adk_model: str | None = None
    perplexity_api_key: str | None = None
    perplexity_model: str = "sonar"
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None
    google_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str | None = None
    grounding_timeout_seconds: float = 8.0

    @property
    def neo4j_configured(self) -> bool:
        return bool(self.neo4j_uri and self.neo4j_user and self.neo4j_password)

    @property
    def google_configured(self) -> bool:
        return bool(self.google_api_key or (self.google_cloud_project and self.google_cloud_location))


def load_settings() -> Settings:
    timeout = os.getenv("GROUNDING_TIMEOUT_SECONDS", "8")
    return Settings(
        runner_backend=os.getenv("CRUCIBLE_RUNNER", "adk").lower(),
        adk_model=os.getenv("CRUCIBLE_ADK_MODEL"),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
        perplexity_model=os.getenv("PERPLEXITY_MODEL", "sonar"),
        neo4j_uri=os.getenv("NEO4J_URI"),
        neo4j_user=os.getenv("NEO4J_USER"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        grounding_timeout_seconds=float(timeout),
    )
