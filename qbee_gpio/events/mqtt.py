import logging
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from typing import Self

from qbee_gpio.events.interface import Event
from qbee_gpio.events.shairport import parse_mqtt as _parse_shairport
from qbee_gpio.mqtt import MQTTClient, MQTTConfig

logger = logging.getLogger(__name__)


class MQTTEventsServer(AsyncExitStack):
    """Receive events defining sound activity and song information."""

    def __init__(
        self,
        config: MQTTConfig,
        process: Callable[[Event], Awaitable],
    ):
        super().__init__()
        self._client = MQTTClient(self.on_receive, config) if config.hostname else None
        self._shairport_topic = config.shairport_topic
        self._process = process

    async def __aenter__(self) -> Self:
        if self._client:
            await self.enter_async_context(self._client)
        return self

    async def on_receive(self, topic: str, data: str) -> None:
        if topic.startswith(f"{self._shairport_topic}/"):
            if event := _parse_shairport(
                topic.removeprefix(f"{self._shairport_topic}/"), data
            ):
                await self._process(event)
        else:
            logger.warning(
                "unhandled topic: %s",
                topic,
            )
            return
