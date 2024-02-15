import contextlib
from dataclasses import dataclass

try:
    from RPi import GPIO
except ModuleNotFoundError:
    from qbee_gpio.gpio.types import GPIO


@dataclass
class GPIOSwitch(contextlib.AbstractContextManager):
    """The only added value is that it can be used as a context manager."""

    # You will have to set up board/BCM mode yourself and this number should reflect that choice.
    pin: int

    def __post_init__(self):
        GPIO.setup(self.pin, GPIO.OUT)

    def __enter__(self):
        GPIO.output(self.pin, True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        GPIO.output(self.pin, False)
