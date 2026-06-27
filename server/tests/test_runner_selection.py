import pytest

from app.adk_runner import load_adk_modules
from app.runner import RunnerUnavailable, make_runner
from app.settings import Settings


def test_default_runner_requires_adk_model() -> None:
    with pytest.raises(RunnerUnavailable, match="CRUCIBLE_ADK_MODEL"):
        make_runner(Settings())


def test_unknown_runner_backend_fails() -> None:
    with pytest.raises(RunnerUnavailable, match="Unsupported CRUCIBLE_RUNNER"):
        make_runner(Settings(runner_backend="unknown"))


def test_adk_runner_requires_model_name() -> None:
    with pytest.raises(RunnerUnavailable, match="CRUCIBLE_ADK_MODEL"):
        make_runner(Settings(runner_backend="adk"))


def test_adk_runner_requires_google_credentials() -> None:
    with pytest.raises(RunnerUnavailable, match="GOOGLE_API_KEY"):
        make_runner(Settings(runner_backend="adk", adk_model="gemini-test"))


def test_local_runner_is_not_available() -> None:
    with pytest.raises(RunnerUnavailable, match="Local deterministic runner has been removed"):
        make_runner(Settings(runner_backend="local"))


def test_adk_import_error_points_to_optional_requirements() -> None:
    def missing_import(_name: str) -> object:
        raise ModuleNotFoundError("No module named 'google'")

    with pytest.raises(RunnerUnavailable, match="requirements-adk"):
        load_adk_modules(missing_import)
