from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager

from qbee_gpio.events import Song


class Display(AbstractAsyncContextManager, ABC):
    @abstractmethod
    async def clear(self) -> None: ...
    @abstractmethod
    async def display_now_playing(self, song: Song) -> None: ...
