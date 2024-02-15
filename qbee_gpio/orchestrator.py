import asyncio
import contextlib
import logging.config
from typing import Optional

from concurrent_tasks import BackgroundTask, LoopExceptionHandler

from qbee_gpio.config import QbeeConfig
from qbee_gpio.gpio import GPIOLCDDisplay, GPIOSwitch
from qbee_gpio.shairport_now_playing_poller import ShairportNowPlayingPoller
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
        self._amp_switch = (
            GPIOSwitch(self._cfg.sound_detection.pin_amp_power)
            if self._cfg.sound_detection.enable
            else None
        )
        self._lcd_switch = (
            GPIOSwitch(self._cfg.lcd.pin_power)
            if self._cfg.sound_detection.enable and self._cfg.lcd
            else None
        )
        self._standby_task = (
            BackgroundTask(self._standby) if self._cfg.sound_detection.enable else None
        )
        self._sound_poller = (
            SoundPoller(self._cfg.sound_detection.driver_path)
            if self._cfg.sound_detection.enable
            else None
        )
        self._now_playing_poller = (
            ShairportNowPlayingPoller(self._cfg.lcd.now_playing_path)
            if self._cfg.lcd.enable
            else None
        )

        self._lock = asyncio.Lock()
        self._poll_sound_task = (
            BackgroundTask(self._poll_sound) if self._sound_poller else None
        )
        self._current_power_stack: Optional[contextlib.AsyncExitStack] = None
        self._poll_now_playing_task = (
            BackgroundTask(self._poll_now_playing) if self._now_playing_poller else None
        )
        self._last_message = (
            self._cfg.lcd.startup_message if self._cfg.lcd.enable else ""
        )
        self._stop_event = asyncio.Event()

    async def __aenter__(self):
        if self._standby_task:
            self.enter_context(self._standby_task)
        self.push_async_callback(self._safe_turn_off)
        if self._poll_sound_task:
            self.enter_context(self._poll_sound_task)
        if self._poll_now_playing_task:
            self.enter_context(self._poll_now_playing_task)
        return self

    async def run(self) -> None:
        logger.debug("starting orchestrator...")
        async with LoopExceptionHandler(stop_func=self._stop):
            async with self:
                logger.info("started orchestrator")
                await self._stop_event.wait()
        logger.info("stopped orchestrator")

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
                await self._safe_turn_on()
            else:
                self._standby_task.create()

    async def _safe_turn_on(self) -> None:
        assert self._amp_switch
        async with self._lock:
            if self._current_power_stack:
                return
            logger.debug("turning on amp")
            stack = contextlib.AsyncExitStack()
            stack.enter_context(self._amp_switch)
            if self._lcd_switch and self._lcd:
                logger.debug("turning on lcd")
                stack.enter_context(self._lcd_switch)
                await stack.enter_async_context(self._lcd)
                await self._print(self._last_message)
            self._current_power_stack = stack

    async def _safe_turn_off(self) -> None:
        async with self._lock:
            if not self._current_power_stack:
                return
            logger.debug("turning off amp and lcd")
            await self._current_power_stack.aclose()
            self._current_power_stack = None

    async def _standby(self) -> None:
        assert self._cfg.sound_detection
        if self._cfg.sound_detection.standby_duration is not None:
            logger.debug("entering standby mode")
            await asyncio.sleep(self._cfg.sound_detection.standby_duration)
            logger.debug("exiting standby mode")
            await self._safe_turn_off()
        if self._cfg.sound_detection.shutdown_command:
            logger.info("shutting down system...")
            await asyncio.create_subprocess_shell(
                self._cfg.sound_detection.shutdown_command,
            )

    # LCD.

    async def _poll_now_playing(self) -> None:
        assert self._now_playing_poller
        assert self._cfg.lcd
        async for event in self._now_playing_poller.poll():
            self._last_message = event.display(self._cfg.lcd.lines)
            await self._print(self._last_message)

    async def _print(self, message: str) -> None:
        assert self._lcd
        await self._lcd.display(message, align=str.center)
