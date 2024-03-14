import asyncio
import contextlib
import logging.config
from typing import List

from concurrent_tasks import BackgroundTask, LoopExceptionHandler

from qbee_gpio.config import QbeeConfig
from qbee_gpio.gpio import GPIOLCDDisplay, gpio_switch
from qbee_gpio.metadata import (
    LibrespotNowPlayingPoller,
    NowPlayingPoller,
    ShairportNowPlayingPoller,
)
from qbee_gpio.sound_poller import SoundPoller

logger = logging.getLogger(__name__)


class QbeeOrchestrator(contextlib.AsyncExitStack):
    """Orchestrate power, sound driver, metadata and display.

    This will run two main background tasks:
    - sound driver activity
    - now playing metadata polling and display update

    When activity is detected, everything is turned on and what is playing is displayed.
    When activity stops, a standby timer starts to turn off if no activity is detected in the meantime.
    """

    def __init__(self, debug: bool = False):
        super().__init__()
        self._cfg = QbeeConfig.load()
        logging.config.dictConfig(self._cfg.log_config)
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        self._lcd = (
            GPIOLCDDisplay(
                pin_register_select=self._cfg.lcd.pin_register_select,
                pin_enable=self._cfg.lcd.pin_enable,
                pin_data_4=self._cfg.lcd.pin_data_4,
                pin_data_5=self._cfg.lcd.pin_data_5,
                pin_data_6=self._cfg.lcd.pin_data_6,
                pin_data_7=self._cfg.lcd.pin_data_7,
                width=self._cfg.lcd.width,
                lines=self._cfg.lcd.lines,
            )
            if self._cfg.lcd.enable
            else None
        )
        self._on_switch = (
            gpio_switch(self._cfg.sound_detection.pin_on)
            if self._cfg.sound_detection.enable
            else None
        )
        self._standby_switch = (
            gpio_switch(self._cfg.sound_detection.pin_standby)
            if self._cfg.sound_detection.enable
            else None
        )
        self._standby_task = (
            BackgroundTask(self._standby) if self._cfg.sound_detection.enable else None
        )
        self._sound_poller = (
            SoundPoller(
                self._cfg.sound_detection.driver_path,
            )
            if self._cfg.sound_detection.enable
            else None
        )

        self._poll_sound_task = (
            BackgroundTask(self._poll_sound) if self._sound_poller else None
        )
        self._poll_now_playing_tasks: List[BackgroundTask] = []
        if self._cfg.lcd.enable and self._cfg.lcd.shairport_metadata_path:
            self._poll_now_playing_tasks.append(
                BackgroundTask(
                    self._poll_now_playing,
                    ShairportNowPlayingPoller(self._cfg.lcd.shairport_metadata_path),
                )
            )
        if self._cfg.lcd.enable and self._cfg.lcd.librespot_metadata_path:
            self._poll_now_playing_tasks.append(
                BackgroundTask(
                    self._poll_now_playing,
                    LibrespotNowPlayingPoller(self._cfg.lcd.librespot_metadata_path),
                )
            )
        self._last_message = self._cfg.lcd.startup_message
        self._stop_event = asyncio.Event()

    async def __aenter__(self):
        self._switch(False)
        self.callback(self._switch, False)
        if self._standby_task:
            self.enter_context(self._standby_task)
        if self._poll_sound_task:
            self.enter_context(self._poll_sound_task)
        if self._lcd:
            await self.enter_async_context(self._lcd)
        for task in self._poll_now_playing_tasks:
            self.enter_context(task)
        return self

    async def run(self) -> None:
        logger.debug("starting orchestrator...")
        async with LoopExceptionHandler(stop_func=self._stop):
            async with self:
                logger.info("started orchestrator")
                await self._stop_event.wait()
        logger.debug("stopped orchestrator")

    async def _stop(self) -> None:
        logger.debug("stopping orchestrator...")
        self._stop_event.set()

    # Sound detection.

    async def _poll_sound(self) -> None:
        assert self._sound_poller
        assert self._standby_task
        async for output in self._sound_poller.poll():
            if output:
                logger.debug("cancelling standby mode")
                self._standby_task.cancel()
                self._switch(True)
                await self._print(self._last_message)
            else:
                await self._print("")  # Clear the display.
                self._standby_task.create()

    async def _standby(self) -> None:
        assert self._cfg.sound_detection
        if self._cfg.sound_detection.standby_duration is not None:
            logger.debug("entering standby mode")
            await asyncio.sleep(self._cfg.sound_detection.standby_duration)
            logger.debug("exiting standby mode")
            self._switch(False)
        if self._cfg.sound_detection.shutdown_command:
            logger.info("shutting down system...")
            await asyncio.create_subprocess_shell(
                self._cfg.sound_detection.shutdown_command,
            )

    # LCD.

    async def _poll_now_playing(self, poller: NowPlayingPoller) -> None:
        async for event in poller.poll():
            self._last_message = event.display(self._cfg.lcd.lines)
            await self._print(self._last_message)

    async def _print(self, message: str) -> None:
        if not self._lcd:
            return
        await self._lcd.display(message, align=str.center)

    # Switches.

    def _switch(self, value: bool) -> None:
        if not self._standby_switch or not self._on_switch:
            return
        logger.debug("turning %s", "on" if value else "off")
        self._on_switch(value)
        self._standby_switch(not value)
