from types import SimpleNamespace

from app.adk_trace import trace_from_event


def test_trace_from_event_extracts_tool_and_sources() -> None:
    event = SimpleNamespace(
        content=SimpleNamespace(
            parts=[
                SimpleNamespace(
                    function_response=SimpleNamespace(
                        name="perplexity_search",
                        response={
                            "status": "ok",
                            "sources": [
                                {
                                    "title": "EDPB guideline",
                                    "url": "https://edpb.europa.eu/example",
                                    "snippet": "Official guidance.",
                                }
                            ],
                        },
                    )
                )
            ]
        )
    )

    trace = trace_from_event(event)

    assert trace.tools_used == ["perplexity_search"]
    assert trace.sources[0].title == "EDPB guideline"
