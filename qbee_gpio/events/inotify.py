import logging
from collections.abc import Awaitable, Callable
from contextlib import ExitStack
from pathlib import Path
from typing import Self

from asyncinotify import Inotify, Mask
from concurrent_tasks import BackgroundTask
from pydantic import BaseModel

from qbee_gpio.events.interface import Event, Playing

logger = logging.getLogger(__name__)


class InotifyEventsConfig(BaseModel):
    sound_driver_path: Path | None = None


class InotifyEvents(ExitStack):
    """Receive events defining sound activity by watching sound driver path."""

    def __init__(
        self,
        config: InotifyEventsConfig,
        process: Callable[[Event], Awaitable],
    ):
        super().__init__()
        self._config = config
        self._process = process
        self._watch_task = BackgroundTask(self._watch)
        self._inotify: Inotify | None = None

    def __enter__(self) -> Self:
        if not self._config.sound_driver_path:
            return self
        self._inotify = Inotify()
        self.enter_context(self._inotify)
        self._inotify.add_watch(
            self._config.sound_driver_path, Mask.OPEN | Mask.CLOSE_WRITE
        )
        self.enter_context(self._watch_task)
        logger.debug("watching sound driver")
        return self

    async def _watch(self) -> None:
        if not self._inotify:
            raise RuntimeError("%s is not started", self)
        async for event in self._inotify:
            output = event.mask == Mask.OPEN
            self._process(Event("unknown", Playing(output)))
