"""Тесты FakeTTSProvider и LocalStorageBackend."""
from pathlib import Path

import pytest

from app.services.storage.local_backend import LocalStorageBackend
from app.services.tts.fake_provider import FakeTTSProvider


@pytest.mark.asyncio
async def test_fake_tts_creates_output_file(tmp_path: Path):
    provider = FakeTTSProvider()
    output_path = tmp_path / "voiceover.mp3"

    result = await provider.synthesize(text="Привет, мир!", output_path=output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_local_storage_resolves_path_within_root(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    backend = LocalStorageBackend()
    resolved = backend.resolve_path("uploads/video.mp4")

    assert str(resolved).startswith(str(tmp_path.resolve()))


def test_local_storage_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    backend = LocalStorageBackend()
    with pytest.raises(ValueError, match="Недопустимый путь"):
        backend.resolve_path("../../../etc/passwd")


def test_local_storage_creates_job_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    backend = LocalStorageBackend()
    workspace = backend.job_workspace("test-job-123")

    assert workspace.exists()
    assert workspace.is_dir()
    assert workspace.name == "test-job-123"
