import asyncio
import logging.config
from contextlib import ExitStack
from typing import Self

from concurrent_tasks import BackgroundTask
from gpiozero import OutputDevice
from pydantic import BaseModel

from qbee_gpio.events import Playing

logger = logging.getLogger(__name__)


class PowerConfig(BaseModel):
    # GPIO PIN configuration (BCM mode).
    pin_on: int
    pin_standby: int
    # Number of seconds to keep amp on after sound has stopped.
    standby_duration: float = 600


class Power(ExitStack):
    """Handle power and standby."""

    def __init__(self, config: PowerConfig):
        super().__init__()
        self._on_switch = OutputDevice(config.pin_on)
        self._standby_switch = OutputDevice(config.pin_standby)
        self._standby_task = BackgroundTask(self._standby, config.standby_duration)

    def __enter__(self) -> Self:
        self.enter_context(self._on_switch)
        self.enter_context(self._standby_switch)
        self._standby_switch.value = True
        self.callback(self._standby_task.cancel)
        logger.debug("started power management")
        return self

    async def process_playing(self, playing: Playing) -> None:
        if playing:
            logger.debug("cancelling standby mode if needed")
            self._standby_task.cancel()
            await self._switch(True)
        else:
            self._standby_task.create()

    async def _standby(self, duration: float) -> None:
        if duration > 0:
            logger.debug("entering standby mode")
            await asyncio.sleep(duration)
            logger.debug("exiting standby mode")
        await self._switch(False)

    async def _switch(self, value: bool) -> None:
        if self._on_switch.value == value:
            return
        logger.debug("turning %s", "on" if value else "off")
        self._on_switch.value = value
        self._standby_switch.value = not value
