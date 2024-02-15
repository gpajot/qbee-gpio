import contextlib
from typing import Iterator

try:
    from RPi import GPIO
except ModuleNotFoundError:
    from qbee_gpio.gpio.types import GPIO


@contextlib.contextmanager
def gpio_setup(mode: int = GPIO.BCM) -> Iterator[None]:
    """Setup and cleanup GPIO through context manager."""
    GPIO.setmode(mode)
    try:
        yield None
    finally:
        GPIO.cleanup()
