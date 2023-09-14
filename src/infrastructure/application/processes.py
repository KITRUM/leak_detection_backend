"""
The main purpose of this module is implementing separate
processes interaction interface.
"""

from threading import Thread
from typing import Any, Callable

from loguru import logger

from src.infrastructure.errors import ProcessErorr

_PROCESSES: dict[str, Thread] = {}

# WARNING: Processes are replaced with threads because of the
#          problems with the shared memory between processes.

# TODO: Get back to the processes after data lake is an external service


def _build_key(namespace: str, key: Any) -> str:
    """Builds the unique key base on the namespace."""

    return f"{namespace}_{str(key)}"


def get(namespace: str, key: Any) -> Thread:
    """Get the process from the register if exist."""

    _key = _build_key(namespace, key)
    try:
        return _PROCESSES[_key]
    except KeyError:
        raise ProcessErorr(message=f"Process {_key} does not exist.")


def cancel(namespace: str, key: Any) -> None:
    """Cancel the process base on the namespace and key."""

    # process: Process = get(namespace, key)
    # process.terminate()
    # _key = _build_key(namespace, key)
    # del _PROCESSES[_key]
    # logger.success(f"The process {_key} is terminated")

    raise NotImplementedError


async def run(namespace: str, key: Any, callback: Callable):
    """Run the process and register it for future management."""

    if (_key := _build_key(namespace, key)) in _PROCESSES.keys():
        raise ProcessErorr(message=f"Process {_key} already exist")

    # process: Process = Process(target=callback, daemon=True)
    # process.start()

    thread = Thread(target=callback, daemon=True)
    thread.start()

    _PROCESSES[_key] = thread

    logger.debug(f"A new background process is added to the queue: {_key}")
