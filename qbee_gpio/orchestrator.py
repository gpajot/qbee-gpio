import asyncio
import logging.config
from contextlib import AsyncExitStack

from concurrent_tasks import BackgroundTask, LoopExceptionHandler
from gpiozero import OutputDevice

from qbee_gpio.config import QbeeConfig
from qbee_gpio.metadata import NowPlayingPoller
from qbee_gpio.sound_poller import SoundPoller

logger = logging.getLogger(__name__)


class QbeeOrchestrator(AsyncExitStack):
    """Orchestrate power, sound driver, metadata and display.

    This will run two main background tasks:
    - sound driver activity
    - now playing metadata polling and display update

    When activity is detected, everything is turned on and what is playing is displayed.
    When activity stops, a standby timer starts to turn off if no activity is detected in the meantime.
    """

    def __init__(self, config: QbeeConfig):
        super().__init__()
        self._on_switch = (
            OutputDevice(config.sound_detection.pin_on)
            if config.sound_detection
            else None
        )
        self._standby_switch = (
            OutputDevice(config.sound_detection.pin_standby)
            if config.sound_detection
            else None
        )
        self._standby_task = (
            BackgroundTask(self._standby, config.sound_detection.standby_duration)
            if config.sound_detection
            else None
        )
        self._sound_poller = (
            SoundPoller(config.sound_detection.driver_path)
            if config.sound_detection
            else None
        )

        self._display = config.display.get_display() if config.display else None
        self._poll_sound_task = (
            BackgroundTask(self._poll_sound) if self._sound_poller else None
        )
        self._poll_now_playing_tasks: list[BackgroundTask] = (
            [
                BackgroundTask(
                    self._poll_now_playing,
                    poller,
                )
                for poller in config.display.get_now_playing_pollers()
            ]
            if config.display
            else []
        )

        self._stop_event = asyncio.Event()

    async def __aenter__(self):
        if self._on_switch and self._standby_switch:
            self.callback(self._on_switch.close)
            self.callback(self._standby_switch.close)
            self._standby_switch.on()
        if self._standby_task:
            self.callback(self._standby_task.cancel)
        if self._display:
            await self.enter_async_context(self._display)
        for task in self._poll_now_playing_tasks:
            self.enter_context(task)
        if self._poll_sound_task:
            self.enter_context(self._poll_sound_task)
        return self

    async def run(self) -> None:
        logger.debug("starting...")
        async with LoopExceptionHandler(stop_func=self._stop):
            async with self:
                logger.info("started")
                await self._stop_event.wait()
        logger.debug("stopped")

    async def _stop(self) -> None:
        logger.debug("stopping...")
        self._stop_event.set()

    async def _poll_sound(self) -> None:
        assert self._sound_poller
        assert self._standby_task
        async for playing in self._sound_poller.poll():
            if playing:
                logger.debug("cancelling standby mode")
                self._standby_task.cancel()
                await self._switch(True)
            else:
                if self._display:
                    await self._display.clear()
                self._standby_task.create()

    async def _standby(self, duration: float) -> None:
        logger.debug("entering standby mode")
        await asyncio.sleep(duration)
        logger.debug("exiting standby mode")
        await self._switch(False)

    async def _poll_now_playing(self, poller: NowPlayingPoller) -> None:
        assert self._display
        async for event in poller.poll():
            await self._display.display_now_playing(event)

    async def _switch(self, value: bool) -> None:
        if self._standby_switch and self._on_switch:
            logger.debug("turning %s", "on" if value else "off")
            self._on_switch.value = value
            self._standby_switch.value = not value
