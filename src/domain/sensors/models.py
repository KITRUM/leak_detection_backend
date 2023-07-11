import numpy as np
from pydantic import validator

from src.domain.templates.models import Template
from src.infrastructure.models import InternalModel

__all__ = ("SensorUncommited", "SensorInDb", "Sensor")


class _SensorBase(InternalModel):
    """This mixin includes shared model fields for all internal models."""

    name: str
    x: np.float32
    y: np.float32
    z: np.float32

    @validator("x", "y", "z", pre=True)
    def convert_primitive(cls, value: float | np.float32) -> np.float32:
        """Since the initial value could be not a numpy type
        it must be converted manually.
        """

        if type(value) == np.float32:
            return value

        return np.float32(value)


class SensorUncommited(_SensorBase):
    """This schema should be used for passing it
    to the repository operation.
    """

    template_id: int


class SensorInDb(SensorUncommited):
    """The internal sensor representation."""

    id: int


class Sensor(_SensorBase):
    """The internal sensor representation with nested data mdoel."""

    id: int
    template: Template
