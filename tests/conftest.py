"""Shared test setup.

``bot.config`` raises at import time when BOT_TOKEN is missing, so a dummy
token is installed before any bot module is imported.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("BOT_TOKEN", "111111:test-token-not-real")
os.environ.setdefault("LOG_LEVEL", "WARNING")
