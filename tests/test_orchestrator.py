from unittest.mock import call

import pytest

from qbee_gpio.config import QbeeConfig
from qbee_gpio.display import Display
from qbee_gpio.events import Event, Playing, Song
from qbee_gpio.orchestrator import QbeeOrchestrator, Session
from qbee_gpio.power import Power, PowerConfig


@pytest.fixture
def events(mocker):
    return mocker.patch("qbee_gpio.orchestrator.UDPEvents")


@pytest.fixture
def display(mocker):
    return mocker.Mock(spec=Display)


@pytest.fixture
def get_display(mocker):
    return mocker.patch("qbee_gpio.display.DisplayConfig.get_display")


@pytest.fixture
def power(mocker):
    power = mocker.MagicMock(spec=Power)
    mocker.patch("qbee_gpio.orchestrator.Power", return_value=power)
    return power


async def _send_events(orchestrator):
    assert orchestrator._session is None
    await orchestrator._process(Event("librespot", Playing(True)))
    await orchestrator._process(Event("librespot", Song(title="name")))
    await orchestrator._process(Event("librespot", Playing(True)))
    await orchestrator._process(Event("librespot", Playing(False)))
    assert orchestrator._session == Session(
        "librespot",
        Song(title="name"),
        Playing(False),
    )


async def test_with_only_power(get_display, power):
    get_display.return_value = None
    async with QbeeOrchestrator(
        QbeeConfig(power=PowerConfig(pin_on=1, pin_standby=2))
    ) as orchestrator:
        assert orchestrator._display is None
        await _send_events(orchestrator)
        assert power.process_playing.call_args_list == [
            call(Playing(True)),
            call(Playing(False)),
        ]


async def test_with_only_display(get_display, display):
    get_display.return_value = display
    async with QbeeOrchestrator(QbeeConfig()) as orchestrator:
        assert orchestrator._power is None
        await _send_events(orchestrator)
    assert display.init.call_count == 2
    assert display.stop.call_count == 3
    display.display_now_playing.assert_called_once_with(Song(title="name"))


async def test_full(get_display, display, power):
    get_display.return_value = display
    async with QbeeOrchestrator(
        QbeeConfig(power=PowerConfig(pin_on=1, pin_standby=2))
    ) as orchestrator:
        await _send_events(orchestrator)
    assert power.process_playing.call_args_list == [
        call(Playing(True)),
        call(Playing(False)),
    ]
    assert display.init.call_count == 2
    assert display.stop.call_count == 3
    display.display_now_playing.assert_called_once_with(Song(title="name"))
