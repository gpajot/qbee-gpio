from pathlib import Path

from qbee_gpio.metadata.interface import NowPlaying
from qbee_gpio.metadata.librespot import LibrespotNowPlayingPoller


async def test_decode():
    poller = LibrespotNowPlayingPoller(Path())

    assert poller._decode(b"something else") is None
    assert poller._decode(
        b"artist:UGluayBGbG95ZA==,"
        b"album:VGhlIERhcmsgU2lkZSBPZiBUaGUgTW9vbiAoMjAxMSBSZW1hc3RlcmVkIFZlcnNpb24p,"
        b"title:TW9uZXkgLSAyMDExIFJlbWFzdGVyZWQgVmVyc2lvbg==\t"
    ) == NowPlaying(
        artist="Pink Floyd",
        album="The Dark Side Of The Moon (2011 Remastered Version)",
        title="Money - 2011 Remastered Version",
    )
