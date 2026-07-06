"""
Абстракция хранилища файлов.

Сейчас используется LocalStorageBackend (файловая система контейнера/volume),
но интерфейс уже спроектирован так, чтобы добавить S3StorageBackend (MinIO/AWS)
без изменения pipeline-кода — pipeline работает только с абсолютными путями,
которые возвращает backend.
"""
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def resolve_path(self, relative_path: str) -> Path:
        """Превращает логический путь job'а в реальный путь на диске/в бакете."""
        raise NotImplementedError

    @abstractmethod
    def job_workspace(self, job_id: str) -> Path:
        """Возвращает (и создаёт при необходимости) рабочую директорию для job_id."""
        raise NotImplementedError
