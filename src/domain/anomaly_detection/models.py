from pydantic import BaseModel

from src.domain.anomaly_detection.constants import AnomalyDeviation
from src.domain.tsd import TsdInDb
from src.infrastructure.models import InternalModel, PublicModel

__all__ = (
    "AnomalyDetectionUncommited",
    "AnomalyDetectionInDb",
    "AnomalyDetection",
    "AnomalyDetectionPublic",
)


class _AnomalyDetectionBase(BaseModel):
    """The base representation of anomaly detection.
    Should be used only for inheritance.
    """

    value: AnomalyDeviation


class AnomalyDetectionUncommited(_AnomalyDetectionBase, InternalModel):
    """This schema should be used for passing it
    to the repository operation.
    """

    time_series_data_id: int


class AnomalyDetectionInDb(AnomalyDetectionUncommited):
    """The internal representation of
    the existed Anomaly detection instance.
    """

    id: int


class AnomalyDetection(_AnomalyDetectionBase, InternalModel):
    """The internal representation of reach Anomaly Detection."""

    id: int
    time_series_data: TsdInDb


class AnomalyDetectionPublic(_AnomalyDetectionBase, PublicModel):
    """The internal representation of reach Anomaly Detection."""

    id: int
    time_series_data: TsdInDb
