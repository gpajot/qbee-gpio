from functools import partial
from typing import Callable

from qbee_gpio.gpio.types import Bit

try:
    from RPi import GPIO
except ModuleNotFoundError:
    from qbee_gpio.gpio.types import GPIO


def gpio_switch(pin: int) -> Callable[[Bit], None]:
    GPIO.setup(pin, GPIO.OUT)
    return partial(GPIO.output, pin)
