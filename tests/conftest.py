import pytest
from crucible.config import Settings
from crucible.agents.base import FakeModelClient
from crucible.grounding.cellar.graph_store import InMemoryGraphStore


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="Run live model tests")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: requires real model credentials — skipped unless --live passed"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live", default=False):
        skip_live = pytest.mark.skip(reason="live tests require --live flag and real credentials")
        for item in items:
            if item.get_closest_marker("live"):
                item.add_marker(skip_live)


def test_settings(**overrides) -> Settings:
    defaults: dict = dict(
        reasoning_model="gemini-2.5-pro",
        fast_model="gemini-2.5-flash",
        google_api_key=None,
        google_cloud_project=None,
        perplexity_api_key=None,
        neo4j_uri=None,
        neo4j_user=None,
        neo4j_password=None,
    )
    defaults.update(overrides)
    return Settings(**defaults)


test_settings.__test__ = False  # prevent pytest from collecting this helper as a test


@pytest.fixture
def fake_client():
    return FakeModelClient(scripted=["pong"])


@pytest.fixture
def settings():
    return test_settings()


@pytest.fixture
def seeded_store():
    """In-memory graph: GDPR + 1995 Directive (repealed by GDPR).

    Shared across test_cellar_graph and test_secv — uses real CELEX numbers
    so swapping in Neo4jGraphStore at demo time requires no assertion changes.
    """
    store = InMemoryGraphStore()
    store.add_work(
        cellar_uuid="gdpr-uuid",
        celex="32016R0679",
        eli="http://data.europa.eu/eli/reg/2016/679/oj",
        title="General Data Protection Regulation",
        work_type="REGULATION",
        date_document="2016-04-27",
    )
    store.add_provision(
        celex="32016R0679",
        provision_id="gdpr-art28",
        article_no="Art. 28",
        heading="Processor",
        text=(
            "Where processing is to be carried out on behalf of a controller, "
            "the controller shall use only processors providing sufficient guarantees "
            "to implement appropriate technical and organisational measures..."
        ),
    )
    store.add_provision(
        celex="32016R0679",
        provision_id="gdpr-art28-3",
        article_no="Art. 28(3)",
        heading="Processor contract",
        text=(
            "Processing by a processor shall be governed by a contract or other legal act "
            "under Union or Member State law, that is binding on the processor with regard "
            "to the controller and that sets out the subject-matter and duration of the "
            "processing, the nature and purpose of the processing..."
        ),
    )
    store.add_work(
        cellar_uuid="dpa95-uuid",
        celex="31995L0046",
        eli="http://data.europa.eu/eli/dir/1995/46/oj",
        title="Data Protection Directive 95/46/EC",
        work_type="DIRECTIVE",
        date_document="1995-10-24",
    )
    store.add_provision(
        celex="31995L0046",
        provision_id="dpa95-art17",
        article_no="Art. 17",
        heading="Security of processing",
        text=(
            "The controller must implement appropriate technical and organisational "
            "measures to protect personal data against accidental or unlawful destruction."
        ),
    )
    store.add_repeals_edge(from_celex="32016R0679", to_celex="31995L0046")
    return store
