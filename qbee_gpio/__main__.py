import asyncio
import logging.config
import sys

from qbee_gpio.config import QbeeConfig
from qbee_gpio.orchestrator import QbeeOrchestrator

cfg = QbeeConfig.load()
logging.config.dictConfig(cfg.logging)
if "-v" in sys.argv:
    logging.getLogger().setLevel(logging.DEBUG)

asyncio.run(QbeeOrchestrator(cfg).run())
