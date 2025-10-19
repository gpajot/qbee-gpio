from dataclasses import dataclass
from typing import Literal


class User(str): ...


@dataclass(kw_only=True, frozen=True)
class Song:
    artist: str = ""
    album: str = ""
    title: str = ""


class Playing(int): ...


type Source = Literal["librespot", "shairport"]


@dataclass(frozen=True)
class Event:
    source: Source
    data: User | Song | Playing
