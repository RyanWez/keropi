"""A small, fixed thread pool for CPU-bound rendering.

``asyncio.to_thread`` uses the default executor, which sizes itself to
``min(32, cpu_count + 4)``. Each in-flight card costs roughly 10 MB, so on a
512 MB instance an unbounded pool is a memory problem waiting for a traffic spike.
"""

import asyncio
import atexit
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, TypeVar

from bot import config

logger = logging.getLogger(__name__)

T = TypeVar("T")

_executor = ThreadPoolExecutor(
    max_workers=max(1, config.RENDER_WORKERS), thread_name_prefix="render"
)
atexit.register(_executor.shutdown, wait=False)


async def run_in_render_pool(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, partial(func, *args, **kwargs))
