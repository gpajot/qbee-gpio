from qbee_gpio.events.interface import Event, Playing, Song
from qbee_gpio.events.librespot import parse


async def test_parse():
    assert parse(b"something else") is None
    assert parse(
        b"artists:Pink Floyd,"
        b"album:The Dark Side Of The Moon (2011 Remastered Version),"
        b"title:Money - 2011 Remastered Version"
    ) == Event(
        "librespot",
        Song(
            artist="Pink Floyd",
            album="The Dark Side Of The Moon (2011 Remastered Version)",
            title="Money - 2011 Remastered Version",
        ),
    )
    assert parse(b"playing") == Event("librespot", Playing(True))
    assert parse(b"stopped") == Event("librespot", Playing(False))
