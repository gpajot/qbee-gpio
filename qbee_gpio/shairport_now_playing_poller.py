import asyncio
import base64
import contextlib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


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


class ShairportNowPlayingPoller(contextlib.AsyncExitStack, asyncio.Protocol):
    """Poll shairport metadata pipe and expose minimal information."""

    RE_METADATA = re.compile(
        # Album info
        f"<item><type>{b'core'.hex()}</type><code>{b'asal'.hex()}</code><length>[0-9]+</length>\n"
        '<data encoding="base64">\n(.*?)</data></item>(?:.|\n)*?'
        # Artist info
        f"<item><type>{b'core'.hex()}</type><code>{b'asar'.hex()}</code><length>[0-9]+</length>\n"
        '<data encoding="base64">\n(.*?)</data></item>(?:.|\n)*?'
        # Title info
        f"<item><type>{b'core'.hex()}</type><code>{b'minm'.hex()}</code><length>[0-9]+</length>\n"
        '<data encoding="base64">\n(.*?)</data></item>'
    )

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        # We need a queue as `data_received` is not async.
        self._received_data: asyncio.Queue[bytes] = asyncio.Queue()

    async def poll(self) -> AsyncIterator[NowPlaying]:
        async with self:
            logger.debug("started now playing poller")
            last_event: Optional[NowPlaying] = None
            async for data in self._receive():
                if match := self.RE_METADATA.search(data.decode()):
                    album, artist, title = tuple(
                        base64.b64decode(e).decode() for e in match.groups()
                    )
                    event = NowPlaying(
                        artist=artist,
                        album=album,
                        title=title,
                    )
                    if event == last_event:
                        continue
                    logger.debug("now playing %r", event)
                    last_event = event
                    yield event

    async def __aenter__(self):
        pipe = self.enter_context(
            open(
                os.open(str(self.path), os.O_RDONLY),
            ),
        )
        transport, _ = await asyncio.get_running_loop().connect_read_pipe(
            lambda: self,
            pipe,
        )
        self.callback(transport.close)
        return self

    def data_received(self, data: bytes) -> None:
        self._received_data.put_nowait(data)

    async def _receive(self) -> AsyncIterator[bytes]:
        while True:
            data = await self._received_data.get()
            yield data
