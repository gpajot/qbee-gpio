import asyncio
import contextlib
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Literal, Sequence, Tuple

try:
    from RPi import GPIO
except ModuleNotFoundError:
    from qbee_gpio.gpio.types import GPIO
from qbee_gpio.gpio.types import Bit


@dataclass
class GPIOLCDDisplay(contextlib.AbstractAsyncContextManager):
    """Hitachi HD44780 LCD controller.
    High level function to display text on the LCD.

    For more information see:
    - Condensed version: https://en.wikipedia.org/wiki/Hitachi_HD44780_LCD_controller
    - Datasheet: https://cdn-shop.adafruit.com/datasheets/HD44780.pdf#page=54
    """

    # PIN setup.
    # You will have to set up board/BCM mode yourself and those numbers should reflect that choice.
    pin_register_select: int
    pin_enable: int
    pin_data_4: int
    pin_data_5: int
    pin_data_6: int
    pin_data_7: int
    # Number of characters per line.
    width: int = 16
    # Number of lines.
    lines: Literal[1, 2, 4] = 2
    line_height: Literal[8, 10] = 8

    _line_addresses: Tuple[int, ...] = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _init: bool = False  # Has the LCD been initialized.

    def __post_init__(self):
        # Set up the line addresses (based on width for more than 2 lines).
        self._line_addresses = (0x00, 0x40, 0x00 + self.width, 0x40 + self.width)
        # Init PINs.
        for pin in (
            self.pin_register_select,
            self.pin_enable,
            self.pin_data_4,
            self.pin_data_5,
            self.pin_data_6,
            self.pin_data_7,
        ):
            GPIO.setup(pin, GPIO.OUT)

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        async with self._lock:
            self._init = False

    async def init(self) -> None:
        async with self._lock:
            # Init LCD.
            GPIO.output(self.pin_register_select, False)
            await asyncio.sleep(0.015)
            # Send 3 times the same command to ensure 8-bit mode.
            await self._send_4_bits(0, 0, 1, 1)
            await asyncio.sleep(0.004)  # Wait a bit more here as per specs.
            await self._send_4_bits(0, 0, 1, 1)
            await self._send_4_bits(0, 0, 1, 1)
            # Now switch to 4-bit.
            await self._send_4_bits(0, 0, 1, 0)
            # Function set.
            await self._send_4_bits(0, 0, 1, 0)
            await self._send_4_bits(
                bool(self.lines > 1),
                bool(self.line_height != 8),
                0,
                0,
            )
            # Display on/off control.
            await self._send_4_bits(0, 0, 0, 0)
            await self._send_4_bits(
                1,
                1,  # Screen on.
                0,  # Cursor off.
                0,  # Cursor blink off.
            )
            # Entry mode set.
            await self._send_4_bits(0, 0, 0, 0)
            await self._send_4_bits(
                0,
                1,
                1,  # Cursor moves right.
                0,  # Display does not shit.
            )
            self._init = True

    async def display(
        self,
        message: str,
        *,
        # Wrap content to spread on all available lines.
        wrap: bool = False,
        # This should be a function that takes a string and the width of the display
        # as arguments and return a string whose length is the same as the display.
        align: Callable[[str, int], str] = str.ljust,
    ) -> None:
        """Display a message on the screen."""
        lines = message.split("\n")
        if wrap:
            wrapped_lines = []
            for line in lines:
                # Convert each line in multiple ones based on the display width.
                wrapped_lines += [
                    line[i : i + self.width] for i in range(0, len(line), self.width)
                ]
            lines = wrapped_lines
        # Only keep lines we can display.
        lines = lines[: self.lines]
        # Add empty lines if needed.
        if len(lines) != self.lines:
            lines += [""] * (self.lines - len(lines))
        # Remove accents and align each line.
        lines = [
            align(remove_accents(line[: self.width]), self.width) for line in lines
        ]
        await self._print_lines(lines)

    async def _print_lines(self, lines: Sequence[str]) -> None:
        async with self._lock:
            if not self._init:
                return
            for i, line in enumerate(lines):
                await self._send_byte(0x80 + self._line_addresses[i])
                for char in line:
                    await self._send_byte(ord(char), True)

    async def _send_byte(self, byte: int, is_char: bool = False) -> None:
        """Send a single byte."""
        # Set the mode (command / char).
        GPIO.output(self.pin_register_select, is_char)
        # Send bits 4-7 then 0-3.
        await self._send_nibble(byte >> 4, is_char)
        await self._send_nibble(byte, is_char)

    async def _send_nibble(self, byte: int, is_char: bool = False) -> None:
        await self._send_4_bits(
            bool(byte & 0x08),
            bool(byte & 0x04),
            bool(byte & 0x02),
            bool(byte & 0x01),
            is_char,
        )

    async def _send_4_bits(
        self,
        bit3: Bit,
        bit2: Bit,
        bit1: Bit,
        bit0: Bit,
        is_char: bool = False,
    ) -> None:
        GPIO.output(self.pin_data_4, bit0)
        GPIO.output(self.pin_data_5, bit1)
        GPIO.output(self.pin_data_6, bit2)
        GPIO.output(self.pin_data_7, bit3)
        await self._enable(is_char)

    async def _enable(self, is_char: bool) -> None:
        await asyncio.sleep(0.000001)
        GPIO.output(self.pin_enable, True)
        await asyncio.sleep(0.000001)
        GPIO.output(self.pin_enable, False)
        await asyncio.sleep(0.0001 if not is_char else 0.000001)


def remove_accents(text: str) -> str:
    """Remove accents from text."""
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ASCII", "ignore")
        .decode("utf-8", "ignore")
    )
