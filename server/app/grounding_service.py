from uuid import uuid4

from .grounding_providers import (
    GroundingProvider,
    Neo4jCellarProvider,
    PerplexityProvider,
    adk_availability,
)
from .schemas import (
    GroundingJob,
    GroundingRequest,
    GroundingSource,
    ToolAvailability,
)
from .settings import Settings, load_settings


class GroundingUnavailable(RuntimeError):
    pass


class GroundingService:
    def __init__(
        self,
        settings: Settings | None = None,
        providers: list[GroundingProvider] | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._providers = providers or [
            PerplexityProvider(self._settings),
            Neo4jCellarProvider(self._settings),
        ]
        self._jobs: dict[str, GroundingJob] = {}

    def tool_statuses(self) -> list[ToolAvailability]:
        return [provider.availability() for provider in self._providers] + [
            adk_availability(self._settings)
        ]

    def create_job(self, request: GroundingRequest) -> GroundingJob:
        providers = self._ready_providers(request)
        if not providers:
            raise GroundingUnavailable("No requested grounding provider is configured.")

        job = GroundingJob(
            id=uuid4().hex,
            status="queued",
            query=request.query,
            requested_tools=request.tools,
        )
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> GroundingJob | None:
        return self._jobs.get(job_id)

    async def run_job(self, job_id: str) -> None:
        job = self._jobs[job_id].model_copy(update={"status": "running"})
        self._jobs[job_id] = job

        sources: list[GroundingSource] = []
        answers: list[str] = []
        tools_used: list[str] = []

        try:
            for provider in self._ready_providers_for_job(job):
                result = await provider.ground(job.query)
                answers.append(f"{provider.name}: {result.answer}")
                sources.extend(result.sources)
                tools_used.append(provider.name)
            self._jobs[job_id] = job.model_copy(
                update={
                    "status": "succeeded",
                    "answer": "\n\n".join(answers),
                    "sources": sources,
                    "tools_used": tools_used,
                }
            )
        except Exception as error:
            self._jobs[job_id] = job.model_copy(
                update={"status": "failed", "error": str(error), "tools_used": tools_used}
            )

    def _ready_providers(self, request: GroundingRequest) -> list[GroundingProvider]:
        wanted = set(request.tools)
        return [
            provider
            for provider in self._providers
            if provider.name in wanted and provider.availability().configured
        ]

    def _ready_providers_for_job(self, job: GroundingJob) -> list[GroundingProvider]:
        return [
            provider
            for provider in self._providers
            if provider.availability().configured and provider.name in job.requested_tools
        ]
