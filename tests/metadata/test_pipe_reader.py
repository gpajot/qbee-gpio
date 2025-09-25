import asyncio
import base64
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


@pytest.fixture
def send_message(path, send_script):
    async def _send(data) -> int:
        process = await asyncio.create_subprocess_shell(
            f'PIPE="{str(path)}" DATA="{data}" . {str(send_script.absolute())}'
        )
        return await process.wait()

    return _send


async def test_receive(path: Path, send_message):
    assert await send_message("ignored") == 0

    pipe_reader = PipeReader(path, own_pipe=True)
    received = []

    async def _read():
        reader = pipe_reader.reader
        i = 0
        while i < 2:
            data = await reader.readuntil(b"\t")
            received.append(data.decode())
            i += 1

    async with pipe_reader:
        read_task = asyncio.create_task(_read())
        assert await send_message("hello") == 0
        assert await send_message("bye") == 0
        await read_task

    assert received == [
        f"data:{base64.b64encode(b'hello').decode()}\t",
        f"data:{base64.b64encode(b'bye').decode()}\t",
    ]
