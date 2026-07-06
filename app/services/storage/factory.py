"""Фабрика StorageBackend по настройке STORAGE_BACKEND."""
from functools import lru_cache

from app.core.config import get_settings
from app.services.storage.base import StorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    settings = get_settings()

    match settings.storage_backend:
        case "local":
            from app.services.storage.local_backend import LocalStorageBackend

            return LocalStorageBackend()
        case "s3":
            raise NotImplementedError(
                "S3StorageBackend пока не реализован — задел на будущее, "
                "интерфейс StorageBackend уже готов к этому расширению."
            )
        case _:
            raise ValueError(f"Неизвестный STORAGE_BACKEND: {settings.storage_backend}")
