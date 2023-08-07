import numpy as np
from pydantic import validator

from src.domain.templates.models import Template
from src.infrastructure.models import InternalModel

__all__ = (
    "SensorBase",
    "SensorUncommited",
    "SensorInDb",
    "Sensor",
    "SensorConfigurationUncommited",
    "SensorConfigurationInDb",
    "SensorCreateSchema",
)


# ************************************************
# ********** Sensor Configuration **********
# ************************************************
class SensorConfigurationUncommited(InternalModel):
    interactive_feedback_mode: bool = False


class SensorConfigurationInDb(SensorConfigurationUncommited):
    id: int


# ************************************************
# ********** Sensor **********
# ************************************************
class SensorBase(InternalModel):
    """This mixin includes shared model fields for all internal models."""

    name: str
    x: np.float64
    y: np.float64
    z: np.float64

    @validator("x", "y", "z", pre=True)
    def convert_primitive(cls, value: float | np.float64) -> np.float64:
        """Since the initial value could be not a numpy type
        it must be converted manually.
        """

        if type(value) == np.float64:
            return value

        return np.float64(value)


class SensorUncommited(SensorBase):
    """This schema should be used for passing it
    to the repository operation.
    """

    configuration_id: int
    template_id: int


class SensorInDb(SensorUncommited):
    """The internal sensor representation."""

    id: int


class Sensor(SensorBase):
    """The internal sensor representation with nested data mdoel."""

    id: int
    configuration: SensorConfigurationInDb
    template: Template


# ************************************************
# ********** Other values objects **********
# ************************************************
class SensorCreateSchema(InternalModel):
    """This value objects encapsulates all data
    that is used in the sensor's ceration process.
    """

    configuration_uncommited: SensorConfigurationUncommited
    template_id: int
    sensor_payload: SensorBase
