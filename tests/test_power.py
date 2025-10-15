import asyncio

import pytest
from gpiozero import OutputDevice

from qbee_gpio.events import Playing
from qbee_gpio.power import Power, PowerConfig


@pytest.fixture
def on_switch(mocker):
    m = mocker.MagicMock(spec=OutputDevice)
    m.value = False
    return m


@pytest.fixture
def standby_switch(mocker):
    m = mocker.MagicMock(spec=OutputDevice)
    m.value = False
    return m


@pytest.fixture
def _mock_gpio(mocker, on_switch, standby_switch):
    mocker.patch(
        "qbee_gpio.power.OutputDevice",
        new=lambda p: on_switch if p == 1 else standby_switch,
    )


@pytest.fixture
def power(_mock_gpio):
    return Power(PowerConfig(pin_on=1, pin_standby=2, standby_duration=0.001))


async def test_lifecycle(power, on_switch, standby_switch):
    def assert_standby():
        assert on_switch.value is False
        assert standby_switch.value is True

    def assert_on():
        assert on_switch.value is True
        assert standby_switch.value is False

    with power:
        assert_standby()
        await power.process_playing(Playing(True))
        assert_on()
        await power.process_playing(Playing(False))
        assert_on()
        await power.process_playing(Playing(True))
        assert_on()
        await power.process_playing(Playing(False))
        await asyncio.sleep(0.002)
        assert_standby()
