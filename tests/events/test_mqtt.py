import pytest

from qbee_gpio.events.interface import Event, Playing
from qbee_gpio.events.mqtt import EventsMQTTConfig, MQTTEventsServer
from qbee_gpio.mqtt import MQTTClient


@pytest.fixture
def process(mocker):
    return mocker.AsyncMock()


@pytest.fixture
def mqtt_client(mocker):
    return mocker.Mock(spec=MQTTClient)


@pytest.fixture
async def events(process, mqtt_client):
    return MQTTEventsServer(EventsMQTTConfig(), mqtt_client, process)


async def test_process_shairport(mocker, events, process):
    mocker.patch(
        "qbee_gpio.events.mqtt.shairport.parse_mqtt",
        return_value=Event("shairport", Playing(True)),
    )
    await events._on_receive("shairport/playing", "1")
    process.assert_called_once_with(Event("shairport", Playing(True)))


async def test_process_none(events, process):
    await events._on_receive("other/playing", "1")
    process.assert_not_called()
