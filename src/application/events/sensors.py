from contextvars import ContextVar

from src.application.data_lake import data_lake
from src.domain.anomaly_detection import AnomalyDetection, AnomalyDeviation
from src.domain.events.sensors import (
    Event,
    EventType,
    EventUncommited,
    services,
)
from src.infrastructure.errors.base import BaseError

CTX_LAST_ANOMALY_DETECTION: ContextVar[AnomalyDetection | None] = ContextVar(
    "last_anomaly_detection", default=None
)


async def process(anomaly_detection: AnomalyDetection):
    """This function represents the engine of producing events
    that are related to the specific sensor.

    TBD. Currently, it is based on the anomaly detection results.
        Might be that it should be changed to the Estimation results.
    """

    _last_anomaly_detection: AnomalyDetection | None = (
        CTX_LAST_ANOMALY_DETECTION.get()
    )

    if (
        _last_anomaly_detection
        and anomaly_detection.value == _last_anomaly_detection.value
    ):
        return

    # Update the last anomaly detection context with the new one
    # if a new one DOES NOT match it
    CTX_LAST_ANOMALY_DETECTION.set(anomaly_detection)

    # Build the event base on the anomaly deviation
    match anomaly_detection.value:
        case AnomalyDeviation.CRITICAL:
            create_schema: EventUncommited = EventUncommited(
                type=EventType.CRITICAL,
                sensor_id=anomaly_detection.time_series_data.sensor_id,
            )
        case AnomalyDeviation.CRITICAL:
            create_schema: EventUncommited = EventUncommited(
                type=EventType.CRITICAL,
                sensor_id=anomaly_detection.time_series_data.sensor_id,
            )
        case _:
            raise BaseError(message="Unsupported event operation")

    event: Event = await services.create(create_schema)

    # Update the data lake
    data_lake.sensors_events[
        anomaly_detection.time_series_data.sensor_id
    ].storage.append(event)
