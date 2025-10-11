from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class NowPlaying:
    artist: str
    album: str
    title: str

    def display(self, lines: int) -> str:
        if lines == 1:
            return self.title
        elif lines == 2:
            return f"{self.artist}\n{self.title}"
        else:
            return f"{self.artist}\n{self.album}\n{self.title}"


class NowPlayingPoller(ABC):
    """Poll metadata and expose minimal information."""

    @abstractmethod
    async def poll(self) -> AsyncIterator[NowPlaying]:
        yield NowPlaying("", "", "")
