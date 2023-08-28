import numpy as np
from pydantic import validator

from src.domain.templates.models import Template
from src.infrastructure.models import InternalModel

__all__ = (
    "SensorBase",
    "SensorUncommited",
    "SensorUpdatePartialSchema",
    "SensorFlat",
    "Sensor",
    "SensorConfigurationUncommited",
    "SensorConfigurationFlat",
    "SensorCreateSchema",
    "SensorConfigurationUpdatePartialSchema",
)


# ************************************************
# ********** Sensor Configuration **********
# ************************************************
class SensorConfigurationUncommited(InternalModel):
    interactive_feedback_mode: bool
    initial_anomaly_detection_baseline: bytes


class SensorConfigurationUpdatePartialSchema(InternalModel):
    """This data model is used for partial updating of the database table.
    If the field is not provided, then
    the repository layer does not care about it.
    """

    interactive_feedback_mode: bool | None = None
    initial_anomaly_detection_baseline: bytes | None = None


class SensorConfigurationFlat(SensorConfigurationUncommited):
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


class SensorUpdatePartialSchema(InternalModel):
    name: str | None = None
    x: np.float64 | None = None
    y: np.float64 | None = None
    z: np.float64 | None = None


class SensorFlat(SensorUncommited):
    """The internal sensor representation."""

    id: int


class Sensor(SensorBase):
    """The internal sensor representation with nested data mdoel."""

    id: int
    configuration: SensorConfigurationFlat
    template: Template


# ************************************************
# ********** Aggregates **********
# ************************************************
class SensorCreateSchema(InternalModel):
    """This value objects encapsulates all data
    that is used in the sensor's ceration process.
    """

    configuration_uncommited: SensorConfigurationUncommited
    template_id: int
    sensor_payload: SensorBase
