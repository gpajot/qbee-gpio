from pydantic import BaseModel

from qbee_gpio.display.interface import Display
from qbee_gpio.display.lcd_display import GPIOLCDDisplay, LCDConfig


class DisplayConfig(BaseModel):
    lcd: LCDConfig | None = None

    def get_display(self) -> Display | None:
        if self.lcd:
            return GPIOLCDDisplay(self.lcd)
        return None
