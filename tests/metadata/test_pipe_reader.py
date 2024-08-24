import asyncio
import base64
import contextlib
import os
from pathlib import Path

import pytest

from qbee_gpio.metadata.pipe_reader import PipeReader


@pytest.fixture
def path():
    return Path(__file__).parent / "test_pipe"


@pytest.fixture
def send_script():
    path = Path(__file__).parent / "pipe.sh"
    path.write_text(
        """#!/usr/bin/bash
if ! [ -p "$PIPE" ] ; then
  exit 0
fi
data=$(printf '%s' "$DATA" | base64)
printf 'data:%s\t' "$data" > "$PIPE"
    """
    )
    path.chmod(0o777)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


@contextlib.contextmanager
def make_fifo(path):
    path.unlink(missing_ok=True)
    os.mkfifo(str(path))
    try:
        yield None
    finally:
        path.unlink(missing_ok=True)


@pytest.fixture
def send_message(path, send_script):
    async def _send(data) -> int:
        process = await asyncio.create_subprocess_shell(
            f'PIPE="{str(path)}"' f' DATA="{data}"' f" . {str(send_script.absolute())}"
        )
        return await process.wait()

    return _send


async def test_receive(path: Path, send_message):
    assert await send_message("ignored") == 0

    reader = PipeReader(path, b"\t")
    received = []

    async def _read():
        async for data in reader._receive():
            received.append(data.decode())
            if len(received) == 2:
                return

    with make_fifo(path):
        async with reader:
            read_task = asyncio.create_task(_read())
            assert await send_message("hello") == 0
            assert await send_message("bye") == 0
            await read_task

    assert received == [
        f"data:{base64.b64encode(b'hello').decode()}",
        f"data:{base64.b64encode(b'bye').decode()}",
    ]
