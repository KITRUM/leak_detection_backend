from enum import Enum
from functools import lru_cache

from src.domain.platforms.models import PlatformInfo
from src.infrastructure.errors import NotFoundError

__all__ = ("Platform",)


class Platform(Enum):
    """The enumeration of supported platforms."""

    TRESTAKK = PlatformInfo(id=1, name="trestakk")
    SNORRE = PlatformInfo(id=2, name="snorre")
    ASKELADD = PlatformInfo(id=3, name="askeladd")
    TROLL = PlatformInfo(id=4, name="troll")

    @classmethod
    @lru_cache
    def get_by_id(cls, id: int) -> "Platform":
        for platform in cls:
            if platform.value.id == id:
                return platform

        raise NotFoundError(
            message="Can not find the platform with the given id"
        )
