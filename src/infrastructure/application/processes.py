"""
The main purpose of this module is implementing separate
processes interaction interface.
"""

import asyncio
from multiprocessing import Process
from typing import Any, Callable, Coroutine

from loguru import logger

from src.infrastructure.errors import ProcessErorr

_PROCESSES: dict[str, Process] = {}

# WARNING: Processes are replaced with threads because of the
#          problems with the shared memory between processes.

# TODO: Get back to the processes after data lake is an external service


def _build_key(namespace: str, key: Any) -> str:
    """Builds the unique key base on the namespace."""

    return f"{namespace}_{str(key)}"


def get(namespace: str, key: Any) -> Process:
    """Get the process from the register if exist."""

    _key = _build_key(namespace, key)
    try:
        return _PROCESSES[_key]
    except KeyError:
        raise ProcessErorr(message=f"Process {_key} does not exist.")


def cancel(namespace: str, key: Any) -> None:
    """Cancel the process base on the namespace and key."""

    process: Process = get(namespace, key)
    process.terminate()
    _key = _build_key(namespace, key)
    del _PROCESSES[_key]
    logger.success(f"The process {_key} is terminated")

    # NOTE: Only for threads
    # raise NotImplementedError


def _run_coro(coro_func: Callable[..., Coroutine], *args, **kwargs) -> None:
    """Run the coroutine in the event loop.
    Used as a helper function for the run function.
    """

    asyncio.run(coro_func(*args, **kwargs))


def run(
    namespace: str,
    key: Any,
    callback: Callable | Callable[..., Coroutine],
    **kwargs: Any,
) -> Process:
    """Run the process and register it for future management.
    If the callback is a coroutine, it will be run in a event loop.
    """

    if (_key := _build_key(namespace, key)) in _PROCESSES.keys():
        raise ProcessErorr(message=f"Process {_key} already exist")

    if asyncio.iscoroutinefunction(callback):
        process: Process = Process(
            target=_run_coro, args=(callback,), kwargs=kwargs, daemon=True
        )
        process.start()
    else:
        process = Process(target=callback, kwargs=kwargs, daemon=True)
        process.start()

    _PROCESSES[_key] = process

    logger.debug(f"Background process: {_key}")

    return process
