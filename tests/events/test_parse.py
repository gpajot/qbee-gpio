import pytest

from qbee_gpio.events.interface import Event, User
from qbee_gpio.events.server import _parse


@pytest.fixture
def _parse_librespot(mocker):
    mocker.patch(
        "qbee_gpio.events.server._parse_librespot",
        new=lambda m: Event("librespot", User(m.decode("utf-8"))),
    )


@pytest.fixture
def _parse_shairport(mocker):
    mocker.patch(
        "qbee_gpio.events.server._parse_shairport",
        new=lambda m: Event("shairport", User(m.decode("utf-8"))),
    )


@pytest.mark.usefixtures("_parse_librespot", "_parse_shairport")
def test_parse():
    assert _parse(b"librespot:msg") == Event("librespot", User("msg"))
    assert _parse(b"msg") == Event("shairport", User("msg"))
