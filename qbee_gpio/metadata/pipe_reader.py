import asyncio
import os
from contextlib import AsyncExitStack, contextmanager
from io import TextIOWrapper
from pathlib import Path
from typing import Iterator

from concurrent_tasks import RobustStream


class PipeReader(AsyncExitStack):
    """Read a named pipe and expose a stream reader over data."""

    def __init__(self, path: Path, *, own_pipe: bool = False):
        super().__init__()
        self._stream = RobustStream(
            connector=self._connect_pipe,
            name=type(self).__name__,
            timeout=5,
        )
        self._path = path
        self._own_pipe = own_pipe
        self._pipe: TextIOWrapper | None = None

    async def __aenter__(self):
        self.enter_context(self._pipe_creator())
        self.callback(self._close_pipe)
        await self.enter_async_context(self._stream)
        return self

    @contextmanager
    def _pipe_creator(self) -> Iterator[None]:
        if self._own_pipe:
            self._path.unlink(missing_ok=True)
        created = False
        if not self._path.exists():
            os.mkfifo(str(self._path))
            created = True
        try:
            yield None
        finally:
            if created:
                self._path.unlink(missing_ok=True)

    def _close_pipe(self) -> None:
        if self._pipe:
            self._pipe.close()

    async def _connect_pipe(self, protocol_factory):
        self._close_pipe()
        # If opening as read only, every time a writer disconnects, the pipe will close.
        # Open it as read-write to avoid having to re-open it for every message.
        self._pipe = open(os.open(str(self._path), os.O_RDWR | os.O_NONBLOCK))
        await asyncio.get_running_loop().connect_read_pipe(protocol_factory, self._pipe)

    @property
    def reader(self) -> asyncio.StreamReader:
        return self._stream.reader
