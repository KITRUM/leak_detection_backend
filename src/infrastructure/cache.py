"""
This is a simple cache implementation base on the python dict.
Might be it is not that fancy but it reduces the complexity before
the application is not deployed to the Equinore plant and there is no
information about which tools could be installed there.
Then, the whole application is developed as a standalone solution.
"""

from datetime import datetime, timedelta
from typing import Any

from pydantic import Field

from src.infrastructure.errors import NotFoundError
from src.infrastructure.models import InternalModel


class CacheEntry(InternalModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    ttl: timedelta | None = None
    instance: Any


class Cache:
    """Simple cache class.
    The redis client is not used since only small amount (<50) of objects
    will be placed in the memory at the same time.

    Example:
        >>> Cache.set(namespace='users', key='13', instance=john)
        >>> john: User = Cache.get(namespace='users', key='13')
    """

    _DATA: dict[str, CacheEntry] = {}

    @staticmethod
    def _build_key(namespace: str, key: Any) -> str:
        return f"{namespace}:{str(key)}"

    @classmethod
    def set(
        cls, namespace: str, key: Any, item: Any, ttl: timedelta | None = None
    ):
        _key = cls._build_key(namespace, key)
        entry = CacheEntry(instance=item, ttl=ttl)

        cls._DATA[_key] = entry

    @classmethod
    def get(cls, namespace: str, key: Any) -> Any:
        _key = cls._build_key(namespace, key)

        try:
            entry: CacheEntry = cls._DATA[_key]
        except KeyError:
            raise NotFoundError

        if entry.ttl and ((datetime.now() - entry.timestamp) > entry.ttl):
            raise NotFoundError

        return entry.instance


def cached(namespace: str, key: str):
    """This decorator could be used for simple functions that return vlaues.
    Just decorate any Coroutine for caching the result.

    If result is not exist in the cache - then await the coroutine,
    store it in a cache and then return.
    """

    def wrapper(coro):
        async def inner(*args, **kwargs):
            try:
                result = Cache.get(namespace, key)
            except NotFoundError:
                result = await coro(*args, **kwargs)
                Cache.set(namespace=namespace, key=key, item=result)

            return result

        return inner

    return wrapper
