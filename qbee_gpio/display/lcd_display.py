import asyncio
import unicodedata
from collections.abc import Callable, Sequence
from functools import partial
from time import monotonic, sleep
from typing import Literal, cast

from gpiozero import OutputDevice
from pydantic import BaseModel

from qbee_gpio.display.interface import Display
from qbee_gpio.events import Song

type Bit = Literal[0, 1]
type HalfByte = tuple[Bit, Bit, Bit, Bit]


class LCDPinConfig(BaseModel):
    """GPIO PIN configuration (BCM mode)."""

    register_select: int
    enable: int
    data_4: int
    data_5: int
    data_6: int
    data_7: int


class LCDConfig(BaseModel):
    pins: LCDPinConfig
    width: int = 16
    lines: Literal[1, 2, 4] = 2
    line_height: Literal[8, 10] = 8


class LCDPins:
    def __init__(self, config: LCDPinConfig):
        self.register_select = OutputDevice(config.register_select)
        self.enable = OutputDevice(config.enable)
        self.data = (
            OutputDevice(config.data_4),
            OutputDevice(config.data_5),
            OutputDevice(config.data_6),
            OutputDevice(config.data_7),
        )

    def close(self) -> None:
        self.register_select.close()
        self.enable.close()
        for pin in self.data:
            pin.close()


class GPIOLCDDisplay(Display):
    """Hitachi HD44780 LCD controller.
    High level function to display text on the LCD.

    For more information see:
    - Condensed version: https://en.wikipedia.org/wiki/Hitachi_HD44780_LCD_controller
    - Datasheet: https://cdn-shop.adafruit.com/datasheets/HD44780.pdf
    """

    def __init__(self, config: LCDConfig):
        self._width = config.width
        self._lines = config.lines
        self._line_height = config.line_height
        self._line_addresses = (0x00, 0x40, 0x00 + self._width, 0x40 + self._width)
        self._pin_cfg = config.pins
        self._pins: LCDPins | None = None

        self._lock = asyncio.Lock()
        self._last_cmd_start = 0.0
        self._last_cmd_wait = 0.0

    async def _exec[**P, R](
        self,
        func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        async with self._lock:
            return await asyncio.get_running_loop().run_in_executor(
                None, partial(func, *args, **kwargs)
            )

    async def init(self) -> None:
        await self._exec(self._init)

    def _init(self) -> None:
        if self._pins:
            return
        self._pins = LCDPins(self._pin_cfg)
        # No need to wait here as if the PI is booted power is already high enough.
        # Send 3 times the same command to ensure 8-bit mode.
        self._write(
            (0, 0, 1, 1),
            # Wait more than 4.1ms here as per specs.
            wait_for=0.005,
        )
        self._write(
            (0, 0, 1, 1),
            # Wait more than 100µs here as per specs.
            wait_for=0.00011,
        )
        self._write((0, 0, 1, 1))
        # Now switch to 4-bit.
        self._write((0, 0, 1, 0))
        # Function set.
        self._write(
            (0, 0, 1, 0),
            (
                1 if self._lines > 1 else 0,
                1 if self._line_height != 8 else 0,
                0,
                0,
            ),
        )
        # Display on/off control.
        self._write(
            (0, 0, 0, 0),
            (
                1,
                1,  # Screen on.
                0,  # Cursor off.
                0,  # Cursor blink off.
            ),
        )
        # Entry mode set.
        self._write(
            (0, 0, 0, 0),
            (
                0,
                1,
                1,  # Cursor moves right.
                0,  # Display does not shift.
            ),
        )
        self._clear()

    async def stop(self):
        await self._exec(self._stop)

    def _stop(self) -> None:
        if not self._pins:
            return
        self._clear()
        self._pins.close()
        self._pins = None

    def _clear(self) -> None:
        # Wait for more than 1.52ms.
        self._write((0, 0, 0, 0), (0, 0, 0, 1), wait_for=0.002)

    async def display_now_playing(self, song: Song) -> None:
        match self._lines:
            case 1:
                message = song.title
            case 2:
                message = f"{song.artist}\n{song.title}"
            case _:
                message = f"{song.artist}\n{song.album}\n{song.title}"
        await self._display(message)

    async def _display(
        self,
        message: str,
        *,
        # This should be a function that takes a string and the width of the display
        # as arguments and return a string whose length is the same as the display.
        align: Callable[[str, int], str] = str.center,
    ) -> None:
        """Display a message on the screen."""
        # Only keep lines we can display.
        lines = message.split("\n")[: self._lines]
        # Add empty lines if needed.
        if len(lines) != self._lines:
            lines += [""] * (self._lines - len(lines))
        # Trim to width, remove accents and align each line.
        lines = [
            align(remove_accents(line[: self._width]), self._width) for line in lines
        ]
        await self._exec(self._print_lines, lines)

    def _print_lines(self, lines: Sequence[str]) -> None:
        if not self._pins:
            raise RuntimeError("LCD is not initialized")
        for i, line in enumerate(lines):
            self._write(
                *get_bits(0x80 + self._line_addresses[i]),
            )
            for char in line:
                self._write(*get_bits(ord(char)), is_cmd=False)

    def _write(
        self,
        high_bits: HalfByte,
        low_bits: HalfByte | None = None,
        is_cmd: bool = True,
        wait_for: float | None = None,
    ) -> None:
        assert self._pins
        self._pins.register_select.value = not is_cmd
        self._send_half_byte(high_bits)
        # Wait until enough time has passed for the previous command to be taken into account.
        if (wait := self._last_cmd_wait - (monotonic() - self._last_cmd_start)) > 0:
            sleep(wait)
            self._last_cmd_wait = 0
        self._pulse_enable()
        if low_bits:
            self._send_half_byte(low_bits)
            self._pulse_enable()
        if is_cmd:
            # Mark the start of the command.
            self._last_cmd_start = monotonic()
            # Wait for more than 37µs unless otherwise specified.
            self._last_cmd_wait = wait_for or 0.0001

    def _send_half_byte(self, bits: HalfByte) -> None:
        assert self._pins
        for pin, bit in zip(self._pins.data, reversed(bits), strict=True):
            pin.value = bit

    def _pulse_enable(self) -> None:
        assert self._pins
        self._pins.enable.value = True
        # Wait more than 450ns.
        sleep(0.000001)
        self._pins.enable.value = False


def get_bits(byte: int) -> tuple[HalfByte, HalfByte]:
    str_bits = tuple(map(int, bin(byte).removeprefix("0b").zfill(8)))
    return cast(HalfByte, str_bits[:4]), cast(HalfByte, str_bits[4:8])


def remove_accents(text: str) -> str:
    """Remove accents from text."""
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ASCII", "ignore")
        .decode("utf-8", "ignore")
    )


async def debug():
    lcd = GPIOLCDDisplay(
        LCDConfig(
            pins=LCDPinConfig(
                register_select=int(input("pin register select: ")),
                enable=int(input("pin enable: ")),
                data_4=int(input("pin data 4: ")),
                data_5=int(input("pin data 5: ")),
                data_6=int(input("pin data 6: ")),
                data_7=int(input("pin data 7: ")),
            )
        )
    )
    await lcd.init()
    try:
        while True:
            await lcd._display(input("message: "))
    finally:
        await lcd.stop()


if __name__ == "__main__":
    asyncio.run(debug())
