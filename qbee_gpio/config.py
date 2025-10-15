import zenconfig
from pydantic import BaseModel, Field

from qbee_gpio.display import DisplayConfig
from qbee_gpio.events import UDPServerConfig
from qbee_gpio.power import PowerConfig


class QbeeConfig(BaseModel, zenconfig.Config):
    udp: UDPServerConfig = UDPServerConfig()
    power: PowerConfig | None = None
    display: DisplayConfig = DisplayConfig()
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
