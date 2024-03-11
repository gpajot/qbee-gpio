import asyncio
import contextlib
import logging
import os
from pathlib import Path
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


class PipeReader(contextlib.AsyncExitStack, asyncio.Protocol):
    """Read a pipe and expose an async iterator over data."""

    def __init__(self, path: Path, chunk_separator: bytes):
        super().__init__()
        self.path = path
        self._chunk_separator = chunk_separator
        # We need a queue as `data_received` is not async.
        self._received_data: asyncio.Queue[bytes] = asyncio.Queue()
        self._transport: Optional[asyncio.ReadTransport] = None

    async def __aenter__(self):
        await self._create_transport()
        self.callback(self._close_transport)
        return self

    async def _create_transport(self) -> None:
        pipe = self.enter_context(
            open(
                os.open(str(self.path), os.O_RDONLY | os.O_NONBLOCK),
            ),
        )
        self._transport, _ = await asyncio.get_running_loop().connect_read_pipe(
            lambda: self,
            pipe,
        )

    def _close_transport(self) -> None:
        if self._transport:
            self._transport.close()

    def data_received(self, data: bytes) -> None:
        logger.debug(data.decode())
        self._received_data.put_nowait(data)

    def connection_lost(self, exc):
        # If no exception it means write end has closed.
        if exc:
            logger.warning("error received while reading %s: %r", self.path, exc)
        # Signal to reconnect.
        self._received_data.put_nowait(b"")

    async def _receive(self) -> AsyncIterator[bytes]:
        buffer = bytearray()
        while True:
            data = await self._received_data.get()
            if not data:
                # Reconnect.
                logger.debug("reconnecting reader of %s", self.path)
                await self._create_transport()
                continue
            buffer += data
            try:
                sep_index = buffer.index(self._chunk_separator)
            except ValueError:
                continue
            yield buffer[:sep_index]
            buffer = buffer[sep_index + len(self._chunk_separator) :]
