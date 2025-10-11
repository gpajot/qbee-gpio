import pytest

from qbee_gpio.gpio.lcd_display import GPIOLCDDisplay


@pytest.mark.parametrize(
    ("width", "message", "align", "expected"),
    [
        (8, "Hello\nQbee!", str.ljust, ["Hello   ", "Qbee!   "]),
        (8, "Hello\nQbee!", str.center, [" Hello  ", " Qbee!  "]),
        (8, "A quite longer first line", str.ljust, ["A quite ", "        "]),
        (8, "éèîå", str.ljust, ["eeia    ", "        "]),
    ],
)
async def test_display(width, message, align, expected, mocker):
    lcd = GPIOLCDDisplay(
        pin_register_select=1,
        pin_enable=2,
        pin_data_4=4,
        pin_data_5=5,
        pin_data_6=6,
        pin_data_7=7,
        width=width,
        lines=2,
    )
    lcd._init = True
    mock_print_lines = mocker.patch.object(lcd, "_print_lines")

    await lcd.display(message, align=align)

    mock_print_lines.assert_awaited_once_with(expected)
