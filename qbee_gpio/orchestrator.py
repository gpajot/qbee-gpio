import logging.config
from contextlib import AsyncExitStack
from dataclasses import dataclass

from qbee_gpio.config import QbeeConfig
from qbee_gpio.events import Event, EventsServer, Playing, Song, Source, User
from qbee_gpio.power import Power

logger = logging.getLogger(__name__)


@dataclass
class Session:
    source: Source
    user: User
    song: Song | None = None
    playing: Playing = Playing(False)


class QbeeOrchestrator(AsyncExitStack):
    """Orchestrate power, sound, song information and display.

    This will process two main events:
    - sound activity
    - song information display

    When activity is detected, everything is turned on and what is playing is displayed.
    When activity stops, a standby timer starts to turn off if no activity is detected in the meantime.
    """

    def __init__(self, config: QbeeConfig):
        super().__init__()
        self._udp_events = EventsServer(
            config.udp,
            self._process,
        )
        self._power = Power(config.power) if config.power else None
        self._display = config.display.get_display()

        self._session: Session | None = None

    async def __aenter__(self):
        if self._power:
            self.enter_context(self._power)
        if self._display:
            await self.enter_async_context(self._display)
        await self.enter_async_context(self._udp_events)
        return self

    def _is_same_source(self, event: Event) -> bool:
        return bool(self._session and self._session.source == event.source)

    async def _process(self, event: Event) -> None:
        match event.data:
            case User():
                if event.data and not self._session:
                    logger.debug("%s connected to %s", event.data, event.source)
                    self._session = Session(event.source, event.data)
                elif not event.data and self._is_same_source(event):
                    assert self._session
                    logger.debug(
                        "%s disconnected from %s",
                        self._session.user,
                        self._session.source,
                    )
                    self._session = None
                    if self._display:
                        await self._display.clear()
            case Playing():
                if not self._is_same_source(event):
                    return
                assert self._session
                if event.data != self._session.playing:
                    logger.debug("start playing" if event.data else "stop playing")
                    self._session.playing = event.data
                    if self._power:
                        await self._power.process_playing(event.data)
            case Song():
                if not self._is_same_source(event):
                    return
                logger.debug("now playing: %r", event.data)
                assert self._session
                if event.data != self._session.song:
                    self._session.song = event.data
                    if self._display:
                        await self._display.display_now_playing(event.data)
