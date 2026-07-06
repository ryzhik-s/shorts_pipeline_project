"""Локальное хранилище файлов на файловой системе (volume в Docker)."""
from pathlib import Path

from app.core.config import get_settings
from app.services.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self) -> None:
        settings = get_settings()
        self._root = settings.storage_local_root
        self._root.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, relative_path: str) -> Path:
        path = (self._root / relative_path).resolve()
        # Защита от path traversal (../../etc/passwd) — простая, но обязательная проверка.
        if not str(path).startswith(str(self._root.resolve())):
            raise ValueError(f"Недопустимый путь вне storage root: {relative_path!r}")
        return path

    def job_workspace(self, job_id: str) -> Path:
        workspace = self._root / "jobs" / job_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace
