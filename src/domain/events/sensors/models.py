from enum import StrEnum, auto

from src.domain.anomaly_detection import AnomalyDeviation
from src.domain.sensors import SensorInDb
from src.infrastructure.models import InternalModel

__all__ = (
    "EventType",
    "EventUncommited",
    "EventInDb",
    "Event",
    "ANOMALY_DEVIATION_TO_EVENT_TYPE_MAPPING",
)


class EventType(StrEnum):
    """Represents the status that is used for colorizing the background
    of the sensor card on the fronend
    """

    CRITICAL = auto()
    OK = auto()
    NOT_AVAILABLE = auto()


class EventUncommited(InternalModel):
    """Represents the create database schema."""

    type: EventType
    sensor_id: int


class EventInDb(EventUncommited):
    id: int


class Event(InternalModel):
    id: int
    type: EventType
    sensor: SensorInDb


ANOMALY_DEVIATION_TO_EVENT_TYPE_MAPPING: dict[AnomalyDeviation, EventType] = {
    AnomalyDeviation.CRITICAL: EventType.CRITICAL,
    AnomalyDeviation.WARNING: EventType.OK,
    AnomalyDeviation.OK: EventType.OK,
}
