"""Тесты фабрики LLMProvider — проверяем правильный выбор реализации по конфигу."""
import pytest

from app.services.llm.fake_provider import FakeLLMProvider
from app.services.llm.factory import get_llm_provider


@pytest.fixture(autouse=True)
def _clear_cache():
    get_llm_provider.cache_clear()
    yield
    get_llm_provider.cache_clear()


def test_factory_returns_fake_provider_by_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    from app.core.config import get_settings

    get_settings.cache_clear()

    provider = get_llm_provider()
    assert isinstance(provider, FakeLLMProvider)


def test_factory_raises_on_openai_without_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_llm_provider()
