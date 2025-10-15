import pytest

from qbee_gpio.events.interface import Event, Playing
from qbee_gpio.events.server import EventsServer, UDPServerConfig


@pytest.fixture
def process(mocker):
    return mocker.AsyncMock()


@pytest.fixture
async def events(process):
    return EventsServer(UDPServerConfig(), process)


async def test_process_event(mocker, events, process):
    mocker.patch(
        "qbee_gpio.events.server._parse",
        return_value=Event("librespot", Playing(True)),
    )
    async with events:
        events.datagram_received(b"...", ("", 0))
    process.assert_called_once_with(Event("librespot", Playing(True)))


async def test_process_none(mocker, events, process):
    mocker.patch(
        "qbee_gpio.events.server._parse",
        return_value=None,
    )
    async with events:
        events.datagram_received(b"...", ("", 0))
    process.assert_not_called()
