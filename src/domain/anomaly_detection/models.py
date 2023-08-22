from enum import Enum, StrEnum, auto

import numpy as np
from pydantic import BaseModel, Field
from stumpy.aampi import aampi

from src.config import settings
from src.domain.tsd import TsdFlat
from src.infrastructure.models import InternalModel

__all__ = (
    "AnomalyDetectionBase",
    "AnomalyDeviation",
    "MatrixProfileLevel",
    "AnomalyDetectionUncommited",
    "AnomalyDetectionFlat",
    "AnomalyDetection",
)


class AnomalyDeviation(StrEnum):
    UNDEFINED = auto()
    CRITICAL = auto()
    WARNING = auto()
    OK = auto()


class MatrixProfileLevel(Enum):
    LOW = 1
    HIGH = 2


class AnomalyDetectionBase(BaseModel):
    """The base representation of anomaly detection.
    Should be used only for inheritance.
    """

    value: AnomalyDeviation
    interactive_feedback_mode: bool = False


class AnomalyDetectionUncommited(AnomalyDetectionBase, InternalModel):
    """This schema should be used for passing it
    to the repository operation.
    """

    time_series_data_id: int


class AnomalyDetectionFlat(AnomalyDetectionUncommited):
    """The internal representation of
    the existed Anomaly detection instance.
    """

    id: int


class AnomalyDetection(AnomalyDetectionBase, InternalModel):
    """The internal representation of reach Anomaly Detection."""

    id: int
    time_series_data: TsdFlat


class MatrixProfile(InternalModel):
    """The Matrix profile intermediate data structure."""

    max_dis: np.float64
    counter: int = 0
    last_values: list[np.float64] = Field(default_factory=list)
    warning: int = settings.anomaly_detection.warning
    alert: int = settings.anomaly_detection.alert
    window: int = settings.anomaly_detection.window_size
    mp_level: MatrixProfileLevel = MatrixProfileLevel.HIGH
    baseline: aampi
    fb_max_dis: np.float64
    fb_historical: list[np.float64] = Field(
        default_factory=list
    )  # all historical data about feedback
    fb_temp: list[np.float64] = Field(
        default_factory=list
    )  # items received during the process
    fb_baseline_start: aampi  #  initial baseline
    fb_baseline: aampi  # same as self.baseline

    # Defines if first `window size` number of values were consumed
    initial_values_full_capacity: bool = False
