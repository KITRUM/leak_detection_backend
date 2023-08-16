from enum import StrEnum, auto

from src.domain.templates import Template
from src.infrastructure.models import InternalModel

__all__ = (
    "EventType",
    "EventUncommited",
    "EventFlat",
    "Event",
)


class EventType(StrEnum):
    """Represents the status that is used for colorizing the background
    of the template card on the fronend
    """

    CRITICAL = auto()
    OK = auto()


class EventUncommited(InternalModel):
    """Represents the create database schema."""

    type: EventType
    template_id: int


class EventFlat(InternalModel):
    id: int
    type: EventType
    template_id: int


class Event(InternalModel):
    id: int
    type: EventType
    template: Template
