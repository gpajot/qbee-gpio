import pytest

from qbee_gpio.events.interface import Event, Playing
from qbee_gpio.events.server import _parse


@pytest.fixture
def _parse_librespot(mocker):
    mocker.patch(
        "qbee_gpio.events.server._parse_librespot",
        new=lambda m: Event("librespot", Playing(bool(m))),
    )


@pytest.fixture
def _parse_shairport(mocker):
    mocker.patch(
        "qbee_gpio.events.server._parse_shairport",
        new=lambda m: Event("shairport", Playing(bool(m))),
    )


@pytest.mark.usefixtures("_parse_librespot", "_parse_shairport")
def test_parse():
    assert _parse(b"librespot:1") == Event("librespot", Playing(True))
    assert _parse(b"1") == Event("shairport", Playing(True))
