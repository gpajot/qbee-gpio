import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING, Awaitable, Callable, Self

from concurrent_tasks import RobustStream, TaskPool
from pydantic import BaseModel

from qbee_gpio.events.interface import Event
from qbee_gpio.events.librespot import parse as _parse_librespot
from qbee_gpio.events.shairport import parse as _parse_shairport

logger = logging.getLogger(__name__)


def _parse(data: bytes) -> Event | None:
    if data.startswith(b"librespot:"):
        return _parse_librespot(data.removeprefix(b"librespot:"))
    return _parse_shairport(data)


class UDPServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    timeout: float = 5


class EventsServer(RobustStream, asyncio.DatagramProtocol):
    """Receive events defining sound activity and song information."""

    def __init__(
        self,
        config: UDPServerConfig,
        process: Callable[[Event], Awaitable],
    ):
        super().__init__(
            connector=partial(
                asyncio.get_running_loop().create_datagram_endpoint,
                local_addr=(config.host, config.port),
            ),
            name="udp-events",
            timeout=config.timeout,
        )
        self._pool = TaskPool(size=1, timeout=config.timeout)

        self._process = process

    async def __aenter__(self) -> Self:
        await self._pool.__aenter__()
        await super().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)
        await self._pool.__aexit__(exc_type, exc_val, exc_tb)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if event := _parse(data):
            self._pool.create_task(self._process(event))

    def error_received(self, exc: Exception) -> None:
        logger.warning("error received: %r", exc)

    if TYPE_CHECKING:

        def connection_made(self, transport) -> None: ...
