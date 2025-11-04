from abc import ABC, abstractmethod

from qbee_gpio.events import Song


class Display(ABC):
    @abstractmethod
    async def init(self) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def display_now_playing(self, song: Song) -> None:
        """:raises RuntimeError if display is not initialized."""
