from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass(kw_only=True, frozen=True)
class Song:
    artist: str = ""
    album: str = ""
    title: str = ""


class Playing(int): ...


Source: TypeAlias = Literal["unknown", "librespot", "shairport"]


@dataclass(frozen=True)
class Event:
    source: Source
    data: Song | Playing
