import pytest

from agent_core import tracing


@pytest.fixture(autouse=True)
def no_tracing(monkeypatch):
    """Unit tests never send traces, whatever TRACING_BACKEND the .env sets."""
    monkeypatch.setenv("TRACING_BACKEND", "none")
    tracing.backend.cache_clear()
    yield
    tracing.backend.cache_clear()
