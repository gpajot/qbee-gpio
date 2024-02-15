import asyncio
import sys

from qbee_gpio.config import QbeeConfig
from qbee_gpio.gpio import gpio_setup
from qbee_gpio.orchestrator import QbeeOrchestrator


async def _run() -> None:
    if "--init-config" in sys.argv:
        QbeeConfig.load().save()
        return
    with gpio_setup():
        await QbeeOrchestrator(debug="-v" in sys.argv).run()


def run() -> None:
    asyncio.run(_run())
