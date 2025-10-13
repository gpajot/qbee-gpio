from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager

from qbee_gpio.metadata import NowPlaying


class Display(AbstractAsyncContextManager, ABC):
    @abstractmethod
    async def clear(self) -> None: ...
    @abstractmethod
    async def display_now_playing(self, metadata: NowPlaying) -> None: ...
