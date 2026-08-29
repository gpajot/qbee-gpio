import pytest

from qbee_gpio.events.interface import Event, Playing
from qbee_gpio.events.mqtt import MQTTEventsServer
from qbee_gpio.mqtt import MQTTConfig


@pytest.fixture
def process(mocker):
    return mocker.AsyncMock()


@pytest.fixture
async def events(process):
    return MQTTEventsServer(MQTTConfig(), process)


async def test_process_shairport(mocker, events, process):
    mocker.patch(
        "qbee_gpio.events.mqtt._parse_shairport",
        return_value=Event("shairport", Playing(True)),
    )
    await events.on_receive("shairport/playing", "1")
    process.assert_called_once_with(Event("shairport", Playing(True)))


async def test_process_none(events, process):
    await events.on_receive("other/playing", "1")
    process.assert_not_called()
