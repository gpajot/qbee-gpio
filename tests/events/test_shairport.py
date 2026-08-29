from qbee_gpio.events.interface import Event, Playing, Song
from qbee_gpio.events.shairport import parse_mqtt, parse_udp


async def test_parse_udp():
    assert parse_udp(b"other") is None
    assert parse_udp(b"ssncmdst...") is None
    assert (
        parse_udp(b"coreasalThe Dark Side Of The Moon (2011 Remastered Version)")
        is None
    )
    assert parse_udp(b"coreasarPink Floyd") is None
    assert parse_udp(b"other") is None
    assert parse_udp(b"coreminmMoney - 2011 Remastered Version") is None
    assert parse_udp(b"ssncmden...") == Event(
        "shairport",
        Song(
            artist="Pink Floyd",
            album="The Dark Side Of The Moon (2011 Remastered Version)",
            title="Money - 2011 Remastered Version",
        ),
    )
    assert parse_udp(b"ssncpbeg") == Event("shairport", Playing(True))
    assert parse_udp(b"ssncpend") == Event("shairport", Playing(False))


async def test_parse_mqtt():
    assert parse_mqtt("other", "...") is None
    assert parse_mqtt("playing", "1") == Event("shairport", Playing(True))
    assert parse_mqtt("playing", "0") == Event("shairport", Playing(False))
    assert (
        parse_mqtt("album", "The Dark Side Of The Moon (2011 Remastered Version)")
        is None
    )
    assert parse_mqtt("artist", "Pink Floyd") is None
    assert parse_mqtt("title", "Money - 2011 Remastered Version") == Event(
        "shairport",
        Song(
            artist="Pink Floyd",
            album="The Dark Side Of The Moon (2011 Remastered Version)",
            title="Money - 2011 Remastered Version",
        ),
    )
