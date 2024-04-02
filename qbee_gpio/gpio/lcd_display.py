import asyncio
import contextlib
import unicodedata
from dataclasses import dataclass, field
from time import monotonic, sleep
from typing import Callable, Literal, Optional, Sequence, Tuple

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
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _init: bool = field(default=False, init=False)  # Has the LCD been initialized.
    _last_cmd_start: float = field(default=0, init=False)
    _last_cmd_wait: float = field(default=0, init=False)

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
        await self.close()

    async def init(self) -> None:
        async with self._lock:
            # Init LCD.
            # No need to wait here as if the PI is booted power is already high enough.
            # Send 3 times the same command to ensure 8-bit mode.
            await self._write(
                (0, 0, 1, 1),
                # Wait more than 4.1ms here as per specs.
                wait_for=0.005,
            )
            await self._write(
                (0, 0, 1, 1),
                # Wait more than 100µs here as per specs.
                wait_for=0.00011,
            )
            await self._write((0, 0, 1, 1))
            # Now switch to 4-bit.
            await self._write((0, 0, 1, 0))
            # Function set.
            await self._write(
                (0, 0, 1, 0),
                (
                    bool(self.lines > 1),
                    bool(self.line_height != 8),
                    0,
                    0,
                ),
            )
            # Display on/off control.
            await self._write(
                (0, 0, 0, 0),
                (
                    1,
                    1,  # Screen on.
                    0,  # Cursor off.
                    0,  # Cursor blink off.
                ),
            )
            # Clear display.
            await self.clear(skip_lock=True)
            # Entry mode set.
            await self._write(
                (0, 0, 0, 0),
                (
                    0,
                    1,
                    1,  # Cursor moves right.
                    0,  # Display does not shift.
                ),
            )
            self._init = True

    async def close(self) -> None:
        async with self._lock:
            if not self._init:
                return
            await self.clear(skip_lock=True)
            self._init = False

    async def clear(self, skip_lock: bool = False) -> None:
        # Wait for more than 1.52ms.
        if skip_lock:
            await self._write((0, 0, 0, 0), (0, 0, 0, 1), wait_for=0.002)
        else:
            if not self._init:
                return
            async with self._lock:
                await self._write((0, 0, 0, 0), (0, 0, 0, 1), wait_for=0.002)

    async def display(
        self,
        message: str,
        *,
        # This should be a function that takes a string and the width of the display
        # as arguments and return a string whose length is the same as the display.
        align: Callable[[str, int], str] = str.center,
    ) -> None:
        """Display a message on the screen."""
        # Only keep lines we can display.
        lines = message.split("\n")[: self.lines]
        # Add empty lines if needed.
        if len(lines) != self.lines:
            lines += [""] * (self.lines - len(lines))
        # Trim to width, remove accents and align each line.
        lines = [
            align(remove_accents(line[: self.width]), self.width) for line in lines
        ]
        await self._print_lines(lines)

    async def _print_lines(self, lines: Sequence[str]) -> None:
        async with self._lock:
            if not self._init:
                return
            for i, line in enumerate(lines):
                await self._write(
                    *get_bits(0x80 + self._line_addresses[i]),
                )
                for char in line:
                    await self._write(*get_bits(ord(char)), is_cmd=False)

    async def _write(
        self,
        high_bits: Tuple[Bit, Bit, Bit, Bit],
        low_bits: Optional[Tuple[Bit, Bit, Bit, Bit]] = None,
        is_cmd: bool = True,
        wait_for: Optional[float] = None,
    ) -> None:
        GPIO.output(self.pin_register_select, not is_cmd)
        self._send_4_bits(*high_bits)
        # Wait until enough time has passed for the previous command to be taken into account.
        if (wait := self._last_cmd_wait - (monotonic() - self._last_cmd_start)) > 0:
            await asyncio.sleep(wait)
            self._last_cmd_wait = 0
        self._pulse_enable()
        if low_bits:
            self._send_4_bits(*low_bits)
            self._pulse_enable()
        if is_cmd:
            # Mark the start of the command.
            self._last_cmd_start = monotonic()
            # Wait for more than 37µs unless otherwise specified.
            self._last_cmd_wait = wait_for or 0.0001

    def _send_4_bits(
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

    def _pulse_enable(self) -> None:
        """Note: this is called often when printing, to avoid too much context switching
        and slowing down display printing if this is done synchronously.
        """
        GPIO.output(self.pin_enable, True)
        # Wait more than 450ns.
        sleep(0.000001)
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
                await lcd.display(input("message: "))
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    asyncio.run(debug())
