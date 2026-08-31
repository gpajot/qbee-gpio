import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Self

from pydantic import BaseModel

from qbee_gpio.events import shairport
from qbee_gpio.events.interface import Event
from qbee_gpio.mqtt import MQTTClient

logger = logging.getLogger(__name__)


class EventsMQTTConfig(BaseModel):
    shairport_topic: str = "shairport"


class MQTTEventsServer(AbstractAsyncContextManager):
    """Receive events defining sound activity and song information."""

    def __init__(
        self,
        config: EventsMQTTConfig,
        client: MQTTClient,
        process: Callable[[Event], Awaitable],
    ):
        self._config = config
        self._client = client
        self._process = process

    async def __aenter__(self) -> Self:
        await self._client.subscribe(
            tuple(
                f"{self._config.shairport_topic}/{topic}"
                for topic in shairport.MQTT_TOPICS
            ),
            self._on_receive,
        )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback): ...

    async def _on_receive(self, topic: str, data: str) -> None:
        if topic.startswith(f"{self._config.shairport_topic}/"):
            if event := shairport.parse_mqtt(
                topic.removeprefix(f"{self._config.shairport_topic}/"),
                data,
            ):
                await self._process(event)
        else:
            logger.warning(
                "unhandled topic: %s",
                topic,
            )
            return
