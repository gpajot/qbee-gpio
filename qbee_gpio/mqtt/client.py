import asyncio
import contextlib
import functools
import logging
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, Concatenate

import aiomqtt
from concurrent_tasks import BackgroundTask

from qbee_gpio.mqtt.config import MQTTConfig

logger = logging.getLogger(__name__)

type RobustFunc[**P, R] = Callable[Concatenate[MQTTClient, P], Coroutine[Any, Any, R]]


def _robust[**P, R](
    error_message: str,
) -> Callable[[RobustFunc[P, R]], RobustFunc[P, R | None]]:
    def _outer(func: RobustFunc[P, R]) -> RobustFunc[P, R | None]:
        @functools.wraps(func)
        async def _inner(self, *args: P.args, **kwargs: P.kwargs) -> R | None:
            if self._closed:
                raise RuntimeError("client is closed")
            while True:
                if self._closed:
                    return None
                await self._connected.wait()
                try:
                    return await func(self, *args, **kwargs)
                except aiomqtt.MqttError as e:
                    logger.warning("%s: %s, reconnecting", error_message, e)
                    await self._reconnect()

        return _inner

    return _outer


class MQTTClient(contextlib.AsyncExitStack):
    def __init__(
        self,
        on_receive: Callable[[str, str], Awaitable],
        config: MQTTConfig,
    ):
        super().__init__()
        self._shairport_topic = config.shairport_topic
        self._on_receive = on_receive
        assert config.hostname
        self._client = aiomqtt.Client(
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password,
            identifier="qbee",
            timeout=config.timeout,
            keepalive=config.keepalive,
        )
        self._connect_task = BackgroundTask(self._connect)
        self._receive_task = BackgroundTask(self._receive_messages)
        self._connected = asyncio.Event()
        self._closed = True
        self._backoff = config.backoff

    async def __aenter__(self):
        self._closed = False
        self.enter_context(self._connect_task)
        self.enter_context(self._receive_task)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)
        if self._connected.is_set():
            self._connected.clear()
            with contextlib.suppress(aiomqtt.MqttError):
                await self._client.__aexit__(exc_type, exc_val, exc_tb)
        self._closed = True

    async def _connect(self) -> None:
        with self._backoff:
            while True:
                await self._backoff.wait()
                try:
                    await self._client.__aenter__()
                    break
                except Exception:
                    logger.warning("could not connect, retrying...", exc_info=True)
        self._connected.set()
        logger.info("connected to mqtt")
        await self.subscribe(f"{self._shairport_topic}/#")

    async def _reconnect(self) -> None:
        if not self._closed and self._connected.is_set():
            self._connected.clear()
            with contextlib.suppress(aiomqtt.MqttError):
                await self._client.__aexit__(None, None, None)
            self._connect_task.create()

    @_robust("error receiving messages")
    async def _receive_messages(self) -> None:
        async for message in self._client.messages:
            try:
                await self._on_receive(
                    message.topic.value,
                    message.payload.decode(),
                )
            except Exception:
                logger.error(
                    "error processing message from topic %s: %s",
                    message.topic.value,
                    message.payload,
                    exc_info=True,
                )

    @_robust("error subscribing to topic")
    async def subscribe(self, topic: str) -> None:
        await self._client.subscribe(topic)
        logger.debug("subscribed to %s", topic)
