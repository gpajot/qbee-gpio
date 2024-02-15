import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from asyncinotify import Inotify, Mask

logger = logging.getLogger(__name__)


@dataclass
class SoundPoller:
    """Poll sound driver activity and expose whether something is playing."""

    # Path to the sound driver.
    driver_path: Path

    async def poll(self) -> AsyncIterator[bool]:
        with Inotify() as inotify:
            inotify.add_watch(self.driver_path, Mask.OPEN | Mask.CLOSE_WRITE)
            logger.debug("started sound poller")
            async for event in inotify:
                output = event.mask == Mask.OPEN
                logger.debug("sound driver %sin use", "" if output else "not ")
                yield output
