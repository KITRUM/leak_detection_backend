from collections import defaultdict, deque
from contextlib import suppress
from functools import partial
from typing import Deque

from loguru import logger

from .models import EventType, EventUncommited

__all__ = ("process",)

# TODO: Change the var-storage to the cache
LAST_SENSORS_EVENTS_TYPES: dict[int, Deque[EventType]] = defaultdict(
    partial(deque, maxlen=3)  # type: ignore[arg-type]
)


async def process(
    sensor_id: int, current_event_type: EventType
) -> EventUncommited | None:
    """This function represents the engine of producing events
    that are related to the specific sensor.
    """

    with suppress(IndexError):
        if current_event_type == LAST_SENSORS_EVENTS_TYPES[sensor_id][-1]:
            return None

    create_schema: EventUncommited = EventUncommited(
        type=current_event_type, sensor_id=sensor_id
    )

    # Update the last event type context with the new one
    # if a new one DOES NOT match it
    LAST_SENSORS_EVENTS_TYPES[sensor_id].append(current_event_type)

    logger.info(f"Sensor[{sensor_id}] event is handled: {current_event_type}")

    return create_schema
