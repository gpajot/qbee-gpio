import logging
from pathlib import Path
from typing import ClassVar, Literal, Optional

import attrs
import zenconfig


@attrs.define
class LCDConfig:
    enable: bool = True
    width: int = 16
    lines: Literal[1, 2, 4] = 2
    # GPIO PIN configuration (BCM mode).
    pin_power: int = 17
    pin_register_select: int = 27
    pin_enable: int = 18
    pin_data_4: int = 25
    pin_data_5: int = 24
    pin_data_6: int = 23
    pin_data_7: int = 22
    now_playing_path: Path = attrs.field(
        default=Path("/tmp/shairport-sync-metadata"),
        converter=Path,
    )
    startup_message: str = "Qbee"


@attrs.define
class SoundDetectionConfig:
    enable: bool = True
    driver_path: Path = attrs.field(
        default=Path("/dev/snd/pcmC0D0p"),
        converter=Path,
    )
    # Number of seconds to keep amp on after sound has stopped.
    standby_duration: Optional[float] = 600
    # Change this as needed or set to None to disable shutdown after standby.
    # The default command will work if
    #   - `$_USER_ $_HOST_ = (root) NOPASWD: /usr/sbin/shutdown` has been added to sudoers
    #   - or the user is root
    shutdown_command: Optional[str] = "sudo shutdown -h now"
    # GPIO PIN configuration (BCM mode).
    pin_amp_power: int = 4


@attrs.define
class QbeeConfig(zenconfig.Config):
    PATH: ClassVar[str] = "~/.qbee.yaml"

    sound_detection: SoundDetectionConfig = SoundDetectionConfig()
    lcd: LCDConfig = LCDConfig()

    # Logging.
    log_config: dict = attrs.field(
        factory=lambda: {
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
                "level": logging.getLevelName(logging.INFO),
                "handlers": ["console"],
            },
        },
    )
