import base64
import logging
import re
from pathlib import Path
from typing import AsyncIterator, Optional

from qbee_gpio.metadata.interface import NowPlayingPoller
from qbee_gpio.metadata.model import NowPlaying
from qbee_gpio.metadata.pipe_reader import PipeReader

logger = logging.getLogger(__name__)


class ShairportNowPlayingPoller(PipeReader, NowPlayingPoller):
    """Poll shairport metadata pipe and expose minimal information."""

    def __init__(self, path: Path):
        super().__init__(
            path,
            f"<item><type>{b'ssnc'.hex()}</type><code>{b'mden'.hex()}</code>".encode(),
        )

    async def poll(self) -> AsyncIterator[NowPlaying]:
        async with self:
            logger.debug("started now playing poller")
            last_event: Optional[NowPlaying] = None
            async for data in self._receive():
                if (event := self._decode(data)) and event != last_event:
                    logger.debug("now playing %r", event)
                    last_event = event
                    yield event

    @staticmethod
    def _get_metadata(data: bytes, code: bytes) -> Optional[str]:
        match = re.search(
            f"<item><type>{b'core'.hex()}</type><code>{code.hex()}</code><length>[0-9]+</length>\n"
            '<data encoding="base64">\n(.*?)</data></item>',
            data.decode(),
        )
        if not match:
            return None
        return base64.b64decode(match.groups()[0]).decode()

    def _decode(self, data: bytes) -> Optional[NowPlaying]:
        if (
            (artist := self._get_metadata(data, b"asar"))
            and (album := self._get_metadata(data, b"asal"))
            and (title := self._get_metadata(data, b"minm"))
        ):
            return NowPlaying(
                artist=artist,
                album=album,
                title=title,
            )
        return None
