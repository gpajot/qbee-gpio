"""
Minimal GPIO types for static typing and mocking in tests.
"""
from typing import Literal, Union

Bit = Union[bool, Literal[0, 1]]


class GPIO:
    OUT = 0
    BCM = 0

    @classmethod
    def setmode(cls, mode: int):
        ...

    @classmethod
    def setup(cls, pin: int, mode: int):
        ...

    @classmethod
    def output(cls, pin: int, value: Bit):
        ...

    @classmethod
    def cleanup(cls):
        ...
