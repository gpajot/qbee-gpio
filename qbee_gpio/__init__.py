import asyncio
import logging.config
import sys

from qbee_gpio.config import QbeeConfig
from qbee_gpio.orchestrator import QbeeOrchestrator


def run() -> None:
    cfg = QbeeConfig.load()
    if "--init-config" in sys.argv:
        cfg.save()
        sys.exit(0)

    logging.config.dictConfig(cfg.logging)
    if "-v" in sys.argv:
        logging.getLogger().setLevel(logging.DEBUG)

    asyncio.run(QbeeOrchestrator(cfg).run())
