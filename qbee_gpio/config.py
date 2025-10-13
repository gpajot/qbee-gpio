from pathlib import Path
from typing import ClassVar, Iterator, Literal

import zenconfig
from pydantic import BaseModel, Field

from qbee_gpio.gpio import Display, GPIOLCDDisplay, LCDConfig
from qbee_gpio.metadata import (
    LibrespotNowPlayingPoller,
    NowPlayingPoller,
    ShairportNowPlayingPoller,
)


class DisplayConfig(BaseModel):
    metadata_pipe_paths: dict[Literal["shairport", "librespot"], Path]
    lcd: LCDConfig

    def get_display(self) -> Display | None:
        return GPIOLCDDisplay(self.lcd)

    def get_now_playing_pollers(self) -> Iterator[NowPlayingPoller]:
        for source, path in self.metadata_pipe_paths.items():
            match source:
                case "shairport":
                    yield ShairportNowPlayingPoller(path)
                case "librespot":
                    yield LibrespotNowPlayingPoller(path)


class SoundDetectionConfig(BaseModel):
    # GPIO PIN configuration (BCM mode).
    pin_on: int
    pin_standby: int
    # We'll watch OPEN and CLOSE_WRITE events to detect sound output.
    driver_path: Path
    # Number of seconds to keep amp on after sound has stopped.
    standby_duration: float = 600


class QbeeConfig(BaseModel, zenconfig.Config):
    PATH: ClassVar[str] = "~/.qbee.yaml"

    sound_detection: SoundDetectionConfig | None = None
    display: DisplayConfig | None = None
    logging: dict = Field(
        default_factory=lambda: {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "formatter": {
                    "validate": True,
                    "format": "%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "formatter",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console"],
            },
        }
    )
