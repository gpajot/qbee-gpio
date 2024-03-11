import contextlib
from abc import ABC, abstractmethod
from typing import AsyncIterator

from qbee_gpio.metadata.model import NowPlaying


class NowPlayingPoller(contextlib.AbstractAsyncContextManager, ABC):
    """Poll metadata and expose minimal information."""

    @abstractmethod
    async def poll(self) -> AsyncIterator[NowPlaying]:
        yield NowPlaying("", "", "")
