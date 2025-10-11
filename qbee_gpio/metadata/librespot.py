import base64
import logging
import re
from pathlib import Path
from typing import AsyncIterator, Optional

from qbee_gpio.metadata.interface import NowPlaying, NowPlayingPoller
from qbee_gpio.metadata.pipe_reader import PipeReader

logger = logging.getLogger(__name__)


class LibrespotNowPlayingPoller(NowPlayingPoller):
    """Poll librespot metadata pipe and expose minimal information."""

    RE_METADATA = re.compile(r"artist:(.*?),album:(.*?),title:(.*)")

    def __init__(self, path: Path):
        self._path = path

    async def poll(self) -> AsyncIterator[NowPlaying]:
        async with PipeReader(self._path, own_pipe=True) as pipe_reader:
            logger.debug("started now playing poller")
            last_event: Optional[NowPlaying] = None
            reader = pipe_reader.reader
            while True:
                data = await reader.readuntil(b"\t")
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
