from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(kw_only=True)
class NowPlaying:
    artist: str = ""
    album: str = ""
    title: str = ""


class NowPlayingPoller(ABC):
    """Poll metadata and expose minimal information."""

    @abstractmethod
    async def poll(self) -> AsyncIterator[NowPlaying]:
        yield NowPlaying()
