from typing import NotRequired, TypedDict

from qbee_gpio.events.interface import Event, Playing, Song, User


class _Song(TypedDict):
    artist: NotRequired[str]
    album: NotRequired[str]
    title: NotRequired[str]


_SONG: _Song = {}


def parse(data: bytes) -> Event | None:
    """Data is sent by type so we need to process a full batch of messages to have the complete stuff."""
    global _SONG
    if data.startswith(b"ssncsnam"):
        return Event(
            "shairport",
            User(data.removeprefix(b"ssncsnam").decode("utf-8") or "unknown"),
        )
    if data.startswith(b"ssncdisc"):
        return Event("shairport", User(""))
    if data == b"ssncpbeg":
        return Event("shairport", Playing(True))
    if data == b"ssncpend":
        return Event("shairport", Playing(False))
    if data.startswith(b"ssncmdst"):
        _SONG = {}
    elif data.startswith(b"coreasar"):
        _SONG["artist"] = data.removeprefix(b"coreasar").decode("utf-8")
    elif data.startswith(b"coreasal"):
        _SONG["album"] = data.removeprefix(b"coreasal").decode("utf-8")
    elif data.startswith(b"coreminm"):
        _SONG["title"] = data.removeprefix(b"coreminm").decode("utf-8")
    elif data.startswith(b"ssncmden"):
        s = Song(**_SONG)
        _SONG = {}
        return Event("shairport", s)
    return None
