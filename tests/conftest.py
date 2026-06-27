import pytest
from crucible.config import Settings
from crucible.agents.base import FakeModelClient


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
