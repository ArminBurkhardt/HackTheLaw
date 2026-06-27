from crucible.config import Settings
from crucible.grounding.perplexity import PerplexityResult
from crucible.grounding.source_policy import SourcePolicy, load_source_policy
from crucible.live_context import collect_grounding


def test_source_policy_allows_subdomains_and_rejects_unlisted_sites():
    policy = SourcePolicy(allowed_domains=("eur-lex.europa.eu", "gesetze-im-internet.de"))

    assert policy.allows("https://eur-lex.europa.eu/legal-content/EN/TXT/")
    assert policy.allows("https://www.gesetze-im-internet.de/bgb/__307.html")
    assert not policy.allows("https://en.wikipedia.org/wiki/German_Civil_Code")
    assert not policy.allows("https://www.reddit.com/r/legaladvice/")


def test_source_policy_loads_yaml_allowlist(tmp_path):
    policy_file = tmp_path / "allowed_sources.yaml"
    policy_file.write_text("allowed_domains:\n  - eur-lex.europa.eu\n", encoding="utf-8")

    policy = load_source_policy(str(policy_file))

    assert policy.allowed_domains == ("eur-lex.europa.eu",)


def test_perplexity_grounding_filters_to_allowed_sources(monkeypatch, tmp_path):
    policy_file = tmp_path / "allowed_sources.yaml"
    policy_file.write_text(
        "allowed_domains:\n  - eur-lex.europa.eu\n  - gesetze-im-internet.de\n",
        encoding="utf-8",
    )

    class FakeClient:
        def search(self, query: str, max_results: int = 5) -> list[PerplexityResult]:
            assert max_results == 8
            return [
                PerplexityResult("Wikipedia", "https://en.wikipedia.org/wiki/SaaS", "blocked"),
                PerplexityResult("BGB", "https://www.gesetze-im-internet.de/bgb/__307.html", "allowed"),
                PerplexityResult("Reddit", "https://reddit.com/r/law/comments/x", "blocked"),
                PerplexityResult("EUR-Lex", "https://eur-lex.europa.eu/legal-content/EN/TXT/", "allowed"),
            ]

    monkeypatch.setattr("crucible.live_context.make_perplexity_client", lambda api_key: FakeClient())
    settings = Settings(
        perplexity_api_key="test-key",
        allowed_sources_path=str(policy_file),
        google_api_key=None,
        google_cloud_project=None,
        neo4j_uri=None,
        neo4j_user=None,
        neo4j_password=None,
    )

    sources, tools = collect_grounding(query="liability cap", settings=settings, use_cellar=False)

    assert [source["title"] for source in sources] == ["BGB", "EUR-Lex"]
    assert all("wikipedia" not in source["url"] and "reddit" not in source["url"] for source in sources)
    assert tools[0]["status"] == "ok"
    assert tools[0]["filtered"] == 2
