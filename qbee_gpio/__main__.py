import asyncio
import logging.config
from typing import Annotated

from concurrent_tasks import LoopExceptionHandler
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from qbee_gpio.config import QbeeConfig
from qbee_gpio.orchestrator import QbeeOrchestrator


class Options(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        cli_prog_name="qbee",
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_shortcuts={"verbose": "v"},
    )

    config: Annotated[
        str,
        Field(description="The path containing the configuration."),
    ]
    verbose: Annotated[bool, Field(description="Show all logs.")] = False


options = Options()
QbeeConfig.YAML_FILE = options.config
config = QbeeConfig()
logging.config.dictConfig(config.logging)
if options.verbose:
    logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

stop_event = asyncio.Event()


async def stop() -> None:
    logger.debug("stopping...")
    stop_event.set()


async def run() -> None:
    logger.debug("starting...")
    async with LoopExceptionHandler(stop_func=stop):
        async with QbeeOrchestrator(config):
            logger.info("started")
            await stop_event.wait()
    logger.debug("stopped")


asyncio.run(run())
