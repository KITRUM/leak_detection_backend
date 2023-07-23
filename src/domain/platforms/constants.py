from enum import Enum
from functools import lru_cache

from src.infrastructure.errors import NotFoundError

from .models import PlatformInfo, TagInfo

__all__ = ("Platform",)


def _trestakk_template_sensor_keys(payload: str) -> TagInfo:
    """
    Return: tuple[
        int: the template number,
        str: the template name,
        int: sensor number(filename numbers after the prefix)
    ]
    """

    identifier = payload.strip()[0:2]

    if int(identifier[1]) < 5:
        return TagInfo(
            template_number=2,
            template_suffix="A",
            sensor_number=int(identifier[1]),
        )
    else:
        return TagInfo(
            template_number=3,
            template_suffix="B",
            sensor_number=int(identifier[1]) - 4,
        )


def _snorre_template_sensor_keys(sensor_name: str) -> TagInfo:
    """
    Return: tuple[
        int: the template number,
        str: the template name,
        int: sensor number(filename numbers after the prefix)
    ]
    """

    template_identifiers = {2: "M", 3: "N", 4: "V", 5: "W", 6: "X", 7: "Z"}
    identifier = sensor_name.strip()[0:2]
    template_identifier = int(identifier[0])
    sensor_identifier = int(identifier[1])

    return TagInfo(
        template_number=template_identifier,
        template_suffix=template_identifiers[template_identifier],
        sensor_number=sensor_identifier,
    )


class Platform(Enum):
    """The enumeration of supported platforms."""

    TRESTAKK = PlatformInfo(
        id=1,
        name="trestakk",
        tag="19XT",
        sensor_keys_callback=_trestakk_template_sensor_keys,
    )
    SNORRE = PlatformInfo(
        id=2,
        name="snorre",
        tag="19H-QI___",
        sensor_keys_callback=_snorre_template_sensor_keys,
    )
    ASKELADD = PlatformInfo(id=3, name="askeladd", tag="not implemented")
    TROLL = PlatformInfo(id=4, name="troll", tag="not implemented")

    @classmethod
    @lru_cache
    def get_by_id(cls, id: int) -> "Platform":
        for platform in cls:
            if platform.value.id == id:
                return platform

        raise NotFoundError(
            message="Can not find the platform with the given id"
        )
