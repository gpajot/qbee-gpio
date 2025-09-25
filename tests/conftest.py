import os
import sys

os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

module = type(sys)("asyncinotify")
module.Inotify = None  # type: ignore[attr-defined]
module.Mask = None  # type: ignore[attr-defined]
sys.modules["asyncinotify"] = module
