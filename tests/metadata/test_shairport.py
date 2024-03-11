from pathlib import Path

from qbee_gpio.metadata.model import NowPlaying
from qbee_gpio.metadata.shairport import ShairportNowPlayingPoller


async def test_decode():
    poller = ShairportNowPlayingPoller(Path())

    assert (
        poller._decode(
            b"<item><type>73736e63</type><code>6d647374</code><length>10</length>"
        )
        is None
    )
    assert poller._decode(
        (
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
    ) == NowPlaying(
        artist="Pink Floyd",
        album="The Dark Side Of The Moon (2011 Remastered Version)",
        title="Money - 2011 Remastered Version",
    )
