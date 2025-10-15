from qbee_gpio.events.interface import Event, Playing, Song, User
from qbee_gpio.events.shairport import parse


async def test_parse():
    assert parse(b"other") is None
    assert parse(b"ssncsnamTest") == Event("shairport", User("Test"))
    assert parse(b"ssncdisc") == Event("shairport", User(""))
    assert parse(b"ssncmdst...") is None
    assert parse(b"coreasalThe Dark Side Of The Moon (2011 Remastered Version)") is None
    assert parse(b"coreasarPink Floyd") is None
    assert parse(b"other") is None
    assert parse(b"coreminmMoney - 2011 Remastered Version") is None
    assert parse(b"ssncmden...") == Event(
        "shairport",
        Song(
            artist="Pink Floyd",
            album="The Dark Side Of The Moon (2011 Remastered Version)",
            title="Money - 2011 Remastered Version",
        ),
    )
    assert parse(b"ssncpbeg") == Event("shairport", Playing(True))
    assert parse(b"ssncpend") == Event("shairport", Playing(False))
