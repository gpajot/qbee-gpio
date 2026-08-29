from pydantic import BaseModel, Field

from qbee_gpio.mqtt.backoff import SequenceBackoff


class MQTTConfig(BaseModel):
    shairport_topic: str = "shairport"
    hostname: str | None = None
    port: int = 1883
    username: str | None = None
    password: str | None = None
    timeout: float = 5
    keepalive: int = 60
    backoff: SequenceBackoff = Field(
        default_factory=lambda: SequenceBackoff(0, 1, 5, 10, 30, 60, 300),
    )
