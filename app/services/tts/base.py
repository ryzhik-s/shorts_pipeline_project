"""Абстрактный интерфейс синтеза речи (та же идея, что и LLMProvider)."""
from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, *, text: str, output_path: Path) -> Path:
        """Озвучивает text и сохраняет аудио (mp3/wav) в output_path. Возвращает путь."""
        raise NotImplementedError
