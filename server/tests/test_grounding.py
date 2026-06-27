from fastapi.testclient import TestClient

from app.grounding_providers import ProviderResult
from app.grounding_service import GroundingService
from app.main import create_app
from app.schemas import GroundingSource, ToolAvailability
from app.settings import Settings
from support import EngineRunnerFixture


class ConfiguredProviderStub:
    name = "perplexity_search"

    def availability(self) -> ToolAvailability:
        return ToolAvailability(
            name=self.name,
            configured=True,
            status="ready",
            detail="Configured provider test double.",
        )

    async def ground(self, query: str) -> ProviderResult:
        return ProviderResult(
            answer=f"Grounded: {query}",
            sources=[GroundingSource(title="Example authority", url="https://example.com")],
        )


def test_tool_status_reports_missing_grounding_config() -> None:
    service = GroundingService(settings=Settings())
    client = TestClient(create_app(runner=EngineRunnerFixture(), grounding_service=service))

    response = client.get("/api/tools")
    tools = response.json()["tools"]

    assert response.status_code == 200
    assert any(tool["name"] == "perplexity_search" for tool in tools)
    assert any(tool["status"] == "missing_config" for tool in tools)
    assert any(tool["name"] == "google_adk_runtime" for tool in tools)


def test_grounding_job_requires_real_configured_provider() -> None:
    service = GroundingService(settings=Settings())
    client = TestClient(create_app(runner=EngineRunnerFixture(), grounding_service=service))

    response = client.post("/api/grounding/jobs", json={"query": "GDPR Article 28 audit rights"})

    assert response.status_code == 503
    assert "No requested grounding provider" in response.json()["detail"]


def test_grounding_job_runs_configured_provider() -> None:
    service = GroundingService(settings=Settings(), providers=[ConfiguredProviderStub()])
    client = TestClient(create_app(runner=EngineRunnerFixture(), grounding_service=service))

    created = client.post(
        "/api/grounding/jobs",
        json={"query": "GDPR Article 28 audit rights", "tools": ["perplexity_search"]},
    )
    job_id = created.json()["job"]["id"]
    fetched = client.get(f"/api/grounding/jobs/{job_id}")
    job = fetched.json()["job"]

    assert created.status_code == 202
    assert fetched.status_code == 200
    assert job["status"] == "succeeded"
    assert job["requested_tools"] == ["perplexity_search"]
    assert job["tools_used"] == ["perplexity_search"]
    assert job["sources"][0]["title"] == "Example authority"
