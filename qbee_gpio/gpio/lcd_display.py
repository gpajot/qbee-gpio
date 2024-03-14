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
    - Datasheet: https://cdn-shop.adafruit.com/datasheets/HD44780.pdf
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
            # No need to wait here as if the PI is booted power is already high enough.
            # Send 3 times the same command to ensure 8-bit mode.
            await self._send_command((0, 0, 1, 1))
            await asyncio.sleep(0.01)  # Wait more than 4.1ms here as per specs.
            await self._send_command((0, 0, 1, 1))
            await asyncio.sleep(0.001)  # Wait more than 100µs here as per specs.
            await self._send_command((0, 0, 1, 1))
            # Now switch to 4-bit.
            await self._send_command((0, 0, 1, 0))
            # Function set.
            await self._send_command(
                (0, 0, 1, 0),
                (
                    bool(self.lines > 1),
                    bool(self.line_height != 8),
                    0,
                    0,
                ),
            )
            # Display on/off control.
            await self._send_command(
                (0, 0, 0, 0),
                (
                    1,
                    1,  # Screen on.
                    0,  # Cursor off.
                    0,  # Cursor blink off.
                ),
            )
            # Clear display.
            await self._send_command((0, 0, 0, 0), (0, 0, 0, 1))
            # Entry mode set.
            await self._send_command(
                (0, 0, 0, 0),
                (
                    0,
                    1,
                    1,  # Cursor moves right.
                    0,  # Display does not shit.
                ),
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
        if not message.strip():
            await self._send_command((0, 0, 0, 0), (0, 0, 0, 1))
            return
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
                await self._send_command(
                    *get_bits(0x80 + self._line_addresses[i]),
                )
                for char in line:
                    await self._send_char(ord(char))

    async def _send_char(self, byte: int) -> None:
        """Send a single byte."""
        # Set the mode.
        GPIO.output(self.pin_register_select, True)
        # Send bits 4-7 then 0-3.
        for bits in get_bits(byte):
            await self._send_4_bits(*bits)

    async def _send_command(
        self,
        *high_and_low_bits: Tuple[Bit, Bit, Bit, Bit],
    ) -> None:
        GPIO.output(self.pin_register_select, False)
        for bits in high_and_low_bits:
            await self._send_4_bits(*bits)
        if high_and_low_bits == ((0, 0, 0, 0), (0, 0, 0, 1)):
            # Wait more than 1.52ms after clear command.
            await asyncio.sleep(0.002)
        else:
            # Wait more than 37µs after other commands.
            await asyncio.sleep(0.00005)

    async def _send_4_bits(
        self,
        bit3: Bit,
        bit2: Bit,
        bit1: Bit,
        bit0: Bit,
    ) -> None:
        GPIO.output(self.pin_data_4, bit0)
        GPIO.output(self.pin_data_5, bit1)
        GPIO.output(self.pin_data_6, bit2)
        GPIO.output(self.pin_data_7, bit3)
        await self._enable()

    async def _enable(self) -> None:
        GPIO.output(self.pin_enable, True)
        await asyncio.sleep(0.000001)
        GPIO.output(self.pin_enable, False)


def get_bits(
    byte: int,
) -> Tuple[Tuple[Bit, Bit, Bit, Bit], Tuple[Bit, Bit, Bit, Bit]]:
    high_bits = byte >> 4
    return (
        (
            bool(high_bits & 0x08),
            bool(high_bits & 0x04),
            bool(high_bits & 0x02),
            bool(high_bits & 0x01),
        ),
        (
            bool(byte & 0x08),
            bool(byte & 0x04),
            bool(byte & 0x02),
            bool(byte & 0x01),
        ),
    )


def remove_accents(text: str) -> str:
    """Remove accents from text."""
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ASCII", "ignore")
        .decode("utf-8", "ignore")
    )


async def debug():
    GPIO.setmode(GPIO.BCM)
    try:
        lcd = GPIOLCDDisplay(
            pin_register_select=int(input("pin register select: ")),
            pin_enable=int(input("pin enable: ")),
            pin_data_4=int(input("pin data 4: ")),
            pin_data_5=int(input("pin data 5: ")),
            pin_data_6=int(input("pin data 6: ")),
            pin_data_7=int(input("pin data 7: ")),
        )
        async with lcd:
            while True:
                await lcd.display(input("message: "), align=str.center)
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    asyncio.run(debug())
