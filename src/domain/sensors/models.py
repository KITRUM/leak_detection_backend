import numpy as np
from pydantic import Field, validator

from src.domain.templates.models import Template
from src.infrastructure.database import SensorsTable
from src.infrastructure.models import InternalModel, PublicModel

__all__ = (
    "SensorCreateRequestBody",
    "SensorUncommited",
    "SensorInDb",
    "SensorPublic",
    "Sensor",
)


# ==================================================
# Public models
# ==================================================
class SensorCreateRequestBody(PublicModel):
    """This data model corresponds to the
    http request body for sensor creation.
    """

    name: str = Field(description="The name of the sensor")
    x: float = Field(description="The x position of the sensor")
    y: float = Field(description="The y position of the sensor")
    z: float = Field(description="The z position of the sensor")


class SensorPublic(SensorCreateRequestBody):
    """The public sensor data model."""

    id: int


# ==================================================
# Internal models
# ==================================================
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
