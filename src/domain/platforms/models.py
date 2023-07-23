from typing import Callable, NoReturn

from pydantic import Field

from src.infrastructure.models import InternalModel

__all__ = ("PlatformInfo", "TagInfo")


def not_implemented_callback(_: str) -> NoReturn:
    raise NotImplementedError("Sensor keys callback is not implemented")


class TagInfo(InternalModel):
    """The value object that is used for the estimation process."""

    template_number: int
    template_suffix: str
    sensor_number: int


class PlatformInfo(InternalModel):
    """
    This internal model represent the Platform in the database.
    It is used in domain.platforms.constants
    """

    id: int
    name: str
    tag: str
    sensor_keys_callback: Callable[[str], TagInfo] = Field(
        default=not_implemented_callback
    )
