from enum import StrEnum, auto

from src.domain.sensors import SensorFlat
from src.infrastructure.models import InternalModel

__all__ = ("EventType", "EventUncommited", "EventFlat", "Event")


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


class EventFlat(EventUncommited):
    id: int


class Event(InternalModel):
    id: int
    type: EventType
    sensor: SensorFlat

    def __str__(self) -> str:
        return f"[{self.type} | sensor_id={self.sensor.id}]"
