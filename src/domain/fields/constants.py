from enum import Enum
from functools import lru_cache

from src.infrastructure.errors import NotFoundError

from .models import FieldInfo, TagInfo

__all__ = ("Field",)


def _trestakk_template_sensor_keys(payload: str) -> TagInfo:
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
    template_identifiers = {2: "M", 3: "N", 4: "V", 5: "W", 6: "X", 7: "Z"}
    identifier = sensor_name.strip()[0:2]
    template_identifier = int(identifier[0])
    sensor_identifier = int(identifier[1])

    return TagInfo(
        template_number=template_identifier,
        template_suffix=template_identifiers[template_identifier],
        sensor_number=sensor_identifier,
    )


class Field(Enum):
    """The enumeration of supported fields."""

    TRESTAKK = FieldInfo(
        id=1,
        name="trestakk",
        tag="19XT",
        sensor_keys_callback=_trestakk_template_sensor_keys,
    )
    SNORRE = FieldInfo(
        id=2,
        name="snorre",
        tag="19H-QI___",
        sensor_keys_callback=_snorre_template_sensor_keys,
    )
    ASKELADD = FieldInfo(id=3, name="askeladd", tag="not implemented")
    TROLL = FieldInfo(id=4, name="troll", tag="not implemented")

    @classmethod
    @lru_cache
    def get_by_id(cls, id: int) -> "Field":
        for field in cls:
            if field.value.id == id:
                return field

        raise NotFoundError(message="Can not find the field with the given id")
