from collections import defaultdict, deque
from contextlib import suppress
from functools import partial
from typing import Deque

from src.application.data_lake import data_lake
from src.domain.anomaly_detection import AnomalyDetection, AnomalyDeviation
from src.domain.events.sensors import (
    Event,
    EventType,
    EventUncommited,
    services,
)
from src.domain.events.sensors.models import (
    ANOMALY_DEVIATION_TO_EVENT_TYPE_MAPPING,
)
from src.infrastructure.errors.base import BaseError

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

    with suppress(IndexError):
        _last_sensor_event_type = LAST_SENSORS_EVENTS_TYPES[sensor_id][-1]
        if (
            ANOMALY_DEVIATION_TO_EVENT_TYPE_MAPPING.get(
                anomaly_detection.value
            )
            == _last_sensor_event_type
        ):
            return None

    # Build the event base on the anomaly deviation
    match anomaly_detection.value:
        case AnomalyDeviation.CRITICAL:
            create_schema: EventUncommited = EventUncommited(
                type=EventType.CRITICAL, sensor_id=sensor_id
            )
        case AnomalyDeviation.OK:
            create_schema = EventUncommited(
                type=EventType.OK, sensor_id=sensor_id
            )
        case _:
            raise BaseError(message="Unsupported event operation")

    event: Event = await services.create(create_schema)

    # Update the last event type context with the new one
    # if a new one DOES NOT match it
    LAST_SENSORS_EVENTS_TYPES[event.sensor.id].append(event.type)

    # Update the data lake
    data_lake.events_by_sensor[event.sensor.id].storage.append(event)

    return event
