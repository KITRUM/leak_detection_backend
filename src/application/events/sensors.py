from collections import defaultdict, deque
from contextlib import suppress
from functools import partial
from typing import Deque

from src.domain.anomaly_detection import AnomalyDetection
from src.domain.events.sensors import (
    Event,
    EventType,
    EventUncommited,
    services,
)
from src.domain.events.sensors.models import (
    ANOMALY_DEVIATION_TO_EVENT_TYPE_MAPPING,
)

LAST_SENSORS_EVENTS_TYPES: dict[int, Deque[EventType]] = defaultdict(
    partial(deque, maxlen=3)  # type: ignore[arg-type]
)


async def process(anomaly_detection: AnomalyDetection) -> Event | None:
    """This function represents the engine of producing events
    that are related to the specific sensor.

    TBD. Currently, it is based on the anomaly detection results.
        Might be that it should be changed to the Estimation results.
    """

    sensor_id: int = anomaly_detection.time_series_data.sensor_id
    current_event_type: EventType = ANOMALY_DEVIATION_TO_EVENT_TYPE_MAPPING[
        anomaly_detection.value
    ]

    with suppress(IndexError):
        if current_event_type == LAST_SENSORS_EVENTS_TYPES[sensor_id][-1]:
            return None

    # Build the event base on the anomaly deviation
    create_schema: EventUncommited = EventUncommited(
        type=current_event_type, sensor_id=sensor_id
    )

    event: Event = await services.create(create_schema)

    # Update the last event type context with the new one
    # if a new one DOES NOT match it
    LAST_SENSORS_EVENTS_TYPES[event.sensor.id].append(event.type)

    return event
