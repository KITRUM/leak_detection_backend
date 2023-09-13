from collections import defaultdict, deque
from contextlib import suppress
from functools import partial
from typing import Deque

from loguru import logger

from ..models import Event, EventType, EventUncommited
from ..services import crud

__all__ = ("process",)

# TODO: Change the var-storage to the cache
LAST_SENSORS_EVENTS_TYPES: dict[int, Deque[EventType]] = defaultdict(
    partial(deque, maxlen=3)  # type: ignore[arg-type]
)


async def process(
    sensor_id: int, current_event_type: EventType
) -> Event | None:
    """This function represents the engine of producing events
    that are related to the specific sensor.
    """

    with suppress(IndexError):
        if current_event_type == LAST_SENSORS_EVENTS_TYPES[sensor_id][-1]:
            return None

    # Build the event base on the anomaly deviation
    create_schema: EventUncommited = EventUncommited(
        type=current_event_type, sensor_id=sensor_id
    )

    event: Event = await crud.create(create_schema)

    # Update the last event type context with the new one
    # if a new one DOES NOT match it
    LAST_SENSORS_EVENTS_TYPES[event.sensor.id].append(event.type)

    logger.info(f"New sensor event has been created: {event}")

    return event
