import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Optional

from asyncinotify import Inotify, Mask

logger = logging.getLogger(__name__)


@dataclass
class SoundPoller:
    """Poll sound driver activity and expose whether something is playing."""

    # Path to the sound driver.
    driver_path: Path
    currently_in_use_command: Optional[str]

    async def poll(self) -> AsyncIterator[bool]:
        with Inotify() as inotify:
            inotify.add_watch(self.driver_path, Mask.OPEN | Mask.CLOSE_WRITE)
            logger.debug("started sound poller")
            # Check whether it's currently playing.
            if self.currently_in_use_command:
                process = await asyncio.create_subprocess_shell(
                    self.currently_in_use_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()
                logger.debug(stdout)
                if stdout:
                    yield True
            async for event in inotify:
                output = event.mask == Mask.OPEN
                logger.debug("sound driver %sin use", "" if output else "not ")
                yield output
