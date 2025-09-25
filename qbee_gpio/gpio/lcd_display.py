import asyncio
import unicodedata
from contextlib import AsyncExitStack
from time import monotonic, sleep
from typing import Callable, Literal, Optional, Sequence, Tuple, TypeAlias, cast

from gpiozero import OutputDevice

Bit: TypeAlias = Literal[0, 1]
HalfByte: TypeAlias = tuple[Bit, Bit, Bit, Bit]


class GPIOLCDDisplay(AsyncExitStack):
    """Hitachi HD44780 LCD controller.
    High level function to display text on the LCD.

    For more information see:
    - Condensed version: https://en.wikipedia.org/wiki/Hitachi_HD44780_LCD_controller
    - Datasheet: https://cdn-shop.adafruit.com/datasheets/HD44780.pdf
    """

    def __init__(
        self,
        # PIN setup (BCM).
        pin_register_select: int,
        pin_enable: int,
        pin_data_4: int,
        pin_data_5: int,
        pin_data_6: int,
        pin_data_7: int,
        # Number of characters per line.
        width: int = 16,
        # Number of lines.
        lines: Literal[1, 2, 4] = 2,
        line_height: Literal[8, 10] = 8,
    ):
        super().__init__()
        self.width = width
        self.lines = lines
        self.line_height = line_height

        self._line_addresses = (0x00, 0x40, 0x00 + self.width, 0x40 + self.width)
        self._lock = asyncio.Lock()
        self._init = False  # Has the LCD been initialized.
        self._last_cmd_start = 0.0
        self._last_cmd_wait = 0.0

        self._register_select_pin = OutputDevice(pin_register_select)
        self._enable_pin = OutputDevice(pin_enable)
        self._data_pins = (
            OutputDevice(pin_data_4),
            OutputDevice(pin_data_5),
            OutputDevice(pin_data_6),
            OutputDevice(pin_data_7),
        )

    async def __aenter__(self):
        for pin in (self._register_select_pin, self._enable_pin, *self._data_pins):
            self.enter_context(pin)
        await self.init()
        self.push_async_callback(self.close)
        return self

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
                    1 if self.lines > 1 else 0,
                    1 if self.line_height != 8 else 0,
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
        high_bits: HalfByte,
        low_bits: Optional[HalfByte] = None,
        is_cmd: bool = True,
        wait_for: Optional[float] = None,
    ) -> None:
        self._register_select_pin.value = not is_cmd
        self._send_half_byte(high_bits)
        # Wait until enough time has passed for the previous command to be taken into account.
        if (wait := self._last_cmd_wait - (monotonic() - self._last_cmd_start)) > 0:
            await asyncio.sleep(wait)
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
        for pin, bit in zip(self._data_pins, bits):
            pin.value = bit

    def _pulse_enable(self) -> None:
        """Note: this is called often when printing, to avoid too much context switching
        and slowing down display printing this is done synchronously.
        """
        self._enable_pin.value = True
        # Wait more than 450ns.
        sleep(0.000001)
        self._enable_pin.value = False


def get_bits(byte: int) -> Tuple[HalfByte, HalfByte]:
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


if __name__ == "__main__":
    asyncio.run(debug())
