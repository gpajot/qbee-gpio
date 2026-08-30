from typing import ClassVar

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from qbee_gpio.display import DisplayConfig
from qbee_gpio.events import EventsMQTTConfig, UDPServerConfig
from qbee_gpio.mqtt import MQTTConfig
from qbee_gpio.power import PowerConfig


class QbeeConfig(BaseSettings):
    udp: UDPServerConfig = UDPServerConfig()
    mqtt: MQTTConfig = MQTTConfig()
    events_mqtt: EventsMQTTConfig = EventsMQTTConfig()
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

    YAML_FILE: ClassVar[str] = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        *_,
        **__,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        if not cls.YAML_FILE:
            raise ValueError("no config path provided")
        return (YamlConfigSettingsSource(settings_cls, yaml_file=cls.YAML_FILE),)
