import logging
from pathlib import Path
from typing import ClassVar, Literal, Optional

import attrs
import zenconfig


@attrs.define
class LCDConfig:
    # Change this to `False` to disable LCD.
    enable: bool = True
    # Size.
    width: int = 16
    lines: Literal[1, 2, 4] = 2
    # GPIO PIN configuration (BCM mode).
    pin_register_select: int = 23
    pin_enable: int = 24
    pin_data_4: int = 4
    pin_data_5: int = 25
    pin_data_6: int = 17
    pin_data_7: int = 18
    shairport_metadata_path: Optional[Path] = attrs.field(
        default=Path("/tmp/shairport-sync-metadata"),
        converter=lambda e: Path(e) if e else None,
    )
    librespot_metadata_path: Optional[Path] = attrs.field(
        default=Path("/tmp/librespot-metadata"),
        converter=lambda e: Path(e) if e else None,
    )
    startup_message: str = "Qbee"


@attrs.define
class SoundDetectionConfig:
    # Change this to `True` to disable sound detection.
    enable: bool = True
    # We'll watch OPEN and CLOSE_WRITE events to detect sound output.
    driver_path: Path = attrs.field(
        default=Path("/dev/snd/pcmC0D0p"),
        converter=Path,
    )
    # Number of seconds to keep amp on after sound has stopped.
    standby_duration: Optional[float] = 600
    # Change this as needed or set to None to disable shutdown after standby.
    # The `sudo shutdown -h now` command will work if:
    #   - `$_USER_ ALL = (root) NOPASWD: /usr/sbin/shutdown` has been added to sudoers
    #   - or the user is root
    shutdown_command: Optional[str] = None
    # GPIO PIN configuration (BCM mode).
    pin_on: int = 27
    pin_standby: int = 22


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
