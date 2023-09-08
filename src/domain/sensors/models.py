import pickle
from datetime import datetime

import numpy as np
from pydantic import validator
from stumpy import aampi

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
# ********** Sensor Configuration entities *******
# ************************************************
class SensorConfigurationUncommited(InternalModel):
    """This schema should be used for passing it
    to the repository operation.
    """

    interactive_feedback_mode: bool
    anomaly_detection_initial_baseline_raw: bytes
    last_baseline_selection_timestamp: datetime | None = None
    last_baseline_update_timestamp: datetime | None = None
    pinned: bool | None = None

    @property
    def anomaly_detection_initial_baseline(self) -> aampi:
        """Converts the database representation of the initial baseline
        which is in bytes into the specific stumpy object.
        """

        return pickle.loads(self.anomaly_detection_initial_baseline_raw)


class SensorConfigurationUpdatePartialSchema(InternalModel):
    """This data model is used for partial updating of the database table.
    If the field is not provided, then
    the repository layer does not care about it.
    """

    pinned: bool | None = None
    interactive_feedback_mode: bool | None = None
    anomaly_detection_initial_baseline_raw: bytes | None = None
    last_baseline_selection_timestamp: datetime | None = None
    last_baseline_update_timestamp: datetime | None = None


class SensorConfigurationFlat(SensorConfigurationUncommited):
    id: int


# ************************************************
# ********** Sensor entities **********
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


# ************************************************
# ********** Aggregates **********
# ************************************************
class Sensor(SensorBase):
    """The internal sensor representation with nested data mdoel."""

    id: int
    configuration: SensorConfigurationFlat
    template: Template


class SensorCreateSchema(InternalModel):
    """This value objects encapsulates all data
    that is used in the sensor's ceration process.
    """

    configuration_uncommited: SensorConfigurationUncommited
    template_id: int
    sensor_payload: SensorBase
