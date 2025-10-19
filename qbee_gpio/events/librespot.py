import re

from qbee_gpio.events.interface import Event, Playing, Song, User

_RE_SONG = re.compile(
    r"artists:(?P<artists>.*?),album:(?P<album>.*?),title:(?P<title>.*)"
)
_RE_USER = re.compile(r"user:(.*)")


def parse(data: bytes) -> Event | None:
    if data == b"playing":
        return Event("librespot", Playing(True))
    elif data == b"stopped":
        return Event("librespot", Playing(False))
    elif (match := _RE_SONG.search(data.decode("utf-8"))) and (
        metadata := match.groupdict()
    ):
        return Event(
            "librespot",
            Song(
                artist=metadata["artists"],
                album=metadata["album"],
                title=metadata["title"],
            ),
        )
    elif match := _RE_USER.search(data.decode("utf-8")):
        return Event("librespot", User(match.groups()[0]))
    return None
