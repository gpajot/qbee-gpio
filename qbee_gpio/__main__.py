import asyncio
import logging.config
import sys

from concurrent_tasks import LoopExceptionHandler

from qbee_gpio.config import QbeeConfig
from qbee_gpio.orchestrator import QbeeOrchestrator

cfg = QbeeConfig.load()
logging.config.dictConfig(cfg.logging)
if "-v" in sys.argv:
    logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger("qbee_gpio")

stop_event = asyncio.Event()


async def stop() -> None:
    logger.debug("stopping...")
    stop_event.set()


async def run() -> None:
    logger.debug("starting...")
    async with LoopExceptionHandler(stop_func=stop):
        async with QbeeOrchestrator(cfg):
            logger.info("started")
            await stop_event.wait()
    logger.debug("stopped")


asyncio.run(run())
