from app.grounding_providers import PERPLEXITY_TRUSTED_DOMAINS
from app.grounding_tools import build_grounding_tools
from app.settings import Settings
import httpx


def test_adk_grounding_tools_are_named_for_function_calling() -> None:
    tools = build_grounding_tools(Settings())

    assert [tool.__name__ for tool in tools] == ["perplexity_search", "neo4j_cellar"]


def test_grounding_tools_report_missing_configuration() -> None:
    tools = {tool.__name__: tool for tool in build_grounding_tools(Settings())}

    assert tools["perplexity_search"]("GDPR Article 28")["status"] == "missing_config"
    assert tools["neo4j_cellar"]("GDPR")["status"] == "missing_config"


def test_perplexity_tool_restricts_search_to_trusted_domains(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class ResponseStub:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"answer": "ok", "search_results": [{"title": "EDPB", "url": "https://edpb.europa.eu"}]}

    class ClientStub:
        def __init__(self, **_kwargs) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, _url: str, **kwargs):
            captured.update(kwargs)
            return ResponseStub()

    monkeypatch.setattr("app.grounding_tools.httpx.Client", ClientStub)
    tools = {tool.__name__: tool for tool in build_grounding_tools(Settings(perplexity_api_key="test"))}

    result = tools["perplexity_search"]("GDPR Article 28")

    assert result["status"] == "ok"
    assert captured["json"]["search_domain_filter"] == PERPLEXITY_TRUSTED_DOMAINS
    assert "wikipedia.org" not in PERPLEXITY_TRUSTED_DOMAINS
    assert "reddit.com" not in PERPLEXITY_TRUSTED_DOMAINS


def test_perplexity_tool_reports_timeout_without_crashing_adk(monkeypatch) -> None:
    class ClientStub:
        def __init__(self, **_kwargs) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("app.grounding_tools.httpx.Client", ClientStub)
    tools = {tool.__name__: tool for tool in build_grounding_tools(Settings(perplexity_api_key="test"))}

    result = tools["perplexity_search"]("GDPR Article 28")

    assert result["status"] == "error"
    assert "Perplexity grounding failed" in result["answer"]
    assert result["sources"] == []
