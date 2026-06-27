import pytest
from crucible.config import Settings
from crucible.agents.base import FakeModelClient


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
        use_real_model=False,
        reasoning_model="gemini-2.5-pro",
        fast_model="gemini-2.5-flash",
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
