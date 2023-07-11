from enum import Enum, StrEnum, auto

import numpy as np
from pydantic import BaseModel, Field
from stumpy.aampi import aampi

from src.config import settings
from src.domain.tsd import TsdInDb
from src.infrastructure.models import InternalModel

__all__ = (
    "AnomalyDetectionBase",
    "AnomalyDeviation",
    "MatrixProfileLevel",
    "AnomalyDetectionUncommited",
    "AnomalyDetectionInDb",
    "AnomalyDetection",
)


class AnomalyDeviation(StrEnum):
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


class AnomalyDetectionUncommited(AnomalyDetectionBase, InternalModel):
    """This schema should be used for passing it
    to the repository operation.
    """

    time_series_data_id: int


class AnomalyDetectionInDb(AnomalyDetectionUncommited):
    """The internal representation of
    the existed Anomaly detection instance.
    """

    id: int


class AnomalyDetection(AnomalyDetectionBase, InternalModel):
    """The internal representation of reach Anomaly Detection."""

    id: int
    time_series_data: TsdInDb


class MatrixProfile(InternalModel):
    """The Matrix profile intermediate data structure."""

    max_dis: np.float32
    counter: int = 0
    last_values: list[np.float32] = Field(default_factory=list)
    warning: int = settings.anomaly_detection.warning
    alert: int = settings.anomaly_detection.alert
    window: int = settings.anomaly_detection.window_size
    mp_level: MatrixProfileLevel = MatrixProfileLevel.HIGH
    baseline: aampi
