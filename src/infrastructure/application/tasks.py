"""
The main purpose of this module is
implementing tasks interaction interface.
"""

from asyncio import Task, create_task
from typing import Any, Callable, Coroutine

from loguru import logger

from src.infrastructure.errors import TaskErorr

_TASKS: dict[str, Task] = {}


def _build_key(namespace: str, key: Any) -> str:
    """Builds the unique key base on the namespace."""

    return f"{namespace}_{str(key)}"


def get(namespace: str, key: Any) -> Task:
    """Get the task from the register if exist."""

    _key = _build_key(namespace, key)
    try:
        return _TASKS[_key]
    except KeyError:
        raise TaskErorr(message=f"Task {_key} does not exist.")


def cancel(namespace: str, key: Any) -> None:
    """Cancel the task base on the namespace and key."""

    task: Task = get(namespace, key)
    task.cancel()
    _key = _build_key(namespace, key)
    del _TASKS[_key]
    logger.success(f"The task {task.get_name()} is cancelled")


# NOTE: It could be refactored to use separate threads instead of coroutines.
#       Create a thread and store the thread by the id/name in the storage.
#       On delete we can stop the thread on demand.
async def run(namespace: str, key: Any, coro: Callable[[], Coroutine]):
    """Run the task and register it for future management."""

    if (_key := _build_key(namespace, key)) in _TASKS.keys():
        raise TaskErorr(message=f"Task {_key} already exist")

    task: Task = create_task(coro(), name=_key)
    _TASKS[_key] = task

    logger.debug(
        f"A new background task is added to the queue: {task.get_name()}"
    )
