import pytest

from qbee_gpio.gpio.lcd_display import GPIOLCDDisplay


@pytest.fixture()
def get_lcd():
    def _get(width, lines):
        return GPIOLCDDisplay(
            pin_register_select=1,
            pin_enable=2,
            pin_data_4=4,
            pin_data_5=5,
            pin_data_6=6,
            pin_data_7=7,
            width=width,
            lines=lines,
        )

    return _get


@pytest.mark.parametrize(
    ("width", "lines", "message", "wrap", "align", "expected"),
    [
        (8, 2, "Hello\nQbee!", False, str.ljust, ["Hello   ", "Qbee!   "]),
        (8, 2, "Hello\nQbee!", False, str.center, [" Hello  ", " Qbee!  "]),
        (8, 2, "A quite longer first line", False, str.ljust, ["A quite ", "        "]),
        (8, 2, "A quite longer first line", True, str.ljust, ["A quite ", "longer f"]),
        (
            8,
            4,
            "A longer first line.\nMore",
            True,
            str.ljust,
            ["A longer", " first l", "ine.    ", "More    "],
        ),
        (
            16,
            2,
            "A longer first line.\nMore",
            True,
            str.center,
            ["A longer first l", "      ine.      "],
        ),
        (8, 2, "éèîå", False, str.ljust, ["eeia    ", "        "]),
    ],
)
async def test_display(width, lines, message, wrap, align, expected, get_lcd, mocker):
    lcd = get_lcd(width, lines)
    lcd._init = True
    mock_print_lines = mocker.patch.object(lcd, "_print_lines")

    await lcd.display(message, wrap=wrap, align=align)

    mock_print_lines.assert_awaited_once_with(expected)
