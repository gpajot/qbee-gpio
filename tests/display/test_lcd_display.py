import pytest

from qbee_gpio.display.lcd_display import (
    GPIOLCDDisplay,
    LCDConfig,
    LCDPinConfig,
    LCDPins,
)


@pytest.mark.parametrize(
    ("width", "message", "align", "expected"),
    [
        (8, "Hello\nQbee!", str.ljust, ["Hello   ", "Qbee!   "]),
        (8, "Hello\nQbee!", str.center, [" Hello  ", " Qbee!  "]),
        (8, "A quite longer first line", str.ljust, ["A quite ", "        "]),
        (
            16,
            "A quite longer first line",
            str.ljust,
            ["A quite longer f", "                "],
        ),
        (4, "éèîå", str.ljust, ["eeia", "    "]),
    ],
)
async def test_display(width, message, align, expected, mocker):
    pin_cfg = LCDPinConfig(
        register_select=1, enable=2, data_4=4, data_5=5, data_6=6, data_7=7
    )
    lcd = GPIOLCDDisplay(LCDConfig(width=width, pins=pin_cfg))
    lcd._pins = LCDPins(pin_cfg)
    mock_print_lines = mocker.patch.object(lcd, "_print_lines")

    await lcd._display(message, align=align)

    mock_print_lines.assert_called_once_with(expected)
