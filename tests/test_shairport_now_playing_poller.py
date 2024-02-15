import asyncio
import os
from pathlib import Path

import pytest

from qbee_gpio.shairport_now_playing_poller import NowPlaying, ShairportNowPlayingPoller


@pytest.fixture()
def path():
    p = Path(__file__).parent / "test_pipe"
    try:
        yield p
    finally:
        p.unlink(missing_ok=True)


@pytest.fixture()
def pipe(path):
    os.mkfifo(str(path))
    # Need to open in both read + write as we cannot write until read side has been opened.
    with open(os.open(str(path), os.O_RDWR)) as f:
        yield f


@pytest.fixture()
async def transport(pipe):
    t, _ = await asyncio.get_running_loop().connect_write_pipe(
        asyncio.BaseProtocol,
        pipe,
    )
    try:
        yield t
    finally:
        t.close()


async def test_poll(path: Path, transport: asyncio.WriteTransport):
    transport.write(
        b"<item><type>73736e63</type><code>6d647374</code><length>10</length>",
    )
    transport.write(
        b'\n<data encoding="base64">\nNDE5NTA3OTYxMA==</data></item>\n'
        b"<item><type>636f7265</type><code>6d706572</code><length>8</length>\n"
        b'<data encoding="base64">\n8doEIsU0dbU=</data></item>\n'
        b"<item><type>636f7265</type><code>6173616c</code><length>51</length>\n"
        b'<data encoding="base64">\n'
        b"VGhlIERhcmsgU2lkZSBPZiBUaGUgTW9vbiAoMjAxMSBSZW1hc3RlcmVkIFZlcnNpb24p</data></item>\n"
        b"<item><type>636f7265</type><code>61736172</code><length>10</length>\n"
        b'<data encoding="base64">\nUGluayBGbG95ZA==</data></item>\n'
        b"<item><type>636f7265</type><code>61736370</code><length>0</length></item>\n"
        b"<item><type>636f7265</type><code>6173676e</code><length>0</length></item>\n"
        b"<item><type>636f7265</type><code>6d696e6d</code><length>31</length>\n"
        b'<data encoding="base64">\nTW9uZXkgLSAyMDExIFJlbWFzdGVyZWQgVmVyc2lvbg==</data></item>\n'
        b"<item><type>636f7265</type><code>63617073</code><length>1</length>\n"
        b'<data encoding="base64">\nAQ==</data></item>\n'
        b"<item><type>636f7265</type><code>6173746d</code><length>4</length>\n"
        b'<data encoding="base64">\nAAXMsA==</data></item>\n'
        b"<item><type>73736e63</type><code>6d64656e</code><length>10</length>\n"
        b'<data encoding="base64">\nNDE5NTA3OTYxMA==</data></item>\n'
    )
    async for event in ShairportNowPlayingPoller(path).poll():
        assert event == NowPlaying(
            artist="Pink Floyd",
            album="The Dark Side Of The Moon (2011 Remastered Version)",
            title="Money - 2011 Remastered Version",
        )
        break
