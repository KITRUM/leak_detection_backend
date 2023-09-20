from enum import StrEnum, auto

from src.infrastructure.models import InternalModel

__all__ = ("EventType", "EventUncommited", "Event")


class EventType(StrEnum):
    """Represents the type of the event that appears
    to an operator in a toster events menu
    """

    ALERT_CRITICAL = auto()
    ALERT_SUCCESS = auto()
    INFO = auto()


class EventUncommited(InternalModel):
    """Represents the create database schema."""

    type: EventType
    message: str


class Event(EventUncommited):
    id: int
