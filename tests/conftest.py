"""Smoke-test config: everything runs MOCK and offline, zero keys.

Env is forced before any agent import (config reads VISTA_BACKEND per call,
but keys load at import — setting first keeps tests hermetic either way).
"""

import os
import sys
from pathlib import Path

os.environ["VISTA_BACKEND"] = "mock"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
