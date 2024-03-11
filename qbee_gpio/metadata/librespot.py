import base64
import logging
import os
import re
from pathlib import Path
from typing import AsyncIterator, Optional

from qbee_gpio.metadata.interface import NowPlayingPoller
from qbee_gpio.metadata.model import NowPlaying
from qbee_gpio.metadata.pipe_reader import PipeReader

logger = logging.getLogger(__name__)


class LibrespotNowPlayingPoller(PipeReader, NowPlayingPoller):
    """Poll librespot metadata pipe and expose minimal information."""

    RE_METADATA = re.compile(r"artist:(.*?),album:(.*?),title:(.*)")

    def __init__(self, path: Path):
        super().__init__(path, b"\t")

    async def __aenter__(self):
        self.path.unlink(missing_ok=True)
        os.mkfifo(str(self.path))
        self.callback(self.path.unlink, missing_ok=True)
        return await super().__aenter__()

    async def poll(self) -> AsyncIterator[NowPlaying]:
        async with self:
            logger.debug("started now playing poller")
            last_event: Optional[NowPlaying] = None
            async for data in self._receive():
                if (event := self._decode(data)) and event != last_event:
                    logger.debug("now playing %r", event)
                    last_event = event
                    yield event

    def _decode(self, data: bytes) -> Optional[NowPlaying]:
        if match := self.RE_METADATA.search(data.decode()):
            artist, album, title = tuple(
                base64.b64decode(e).decode() for e in match.groups()
            )
            return NowPlaying(
                artist=", ".join(artist.strip().split("\n")),
                album=album,
                title=title,
            )
        return None
