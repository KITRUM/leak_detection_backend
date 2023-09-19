"""
This module takes over setting up the communication between
application domains in order to provide the high-level feature
called `ANOMALY DETECTION`.

It depends on:
    - the time series data that is fetched from the external source,
    - fields
    - anomaly deviation calculation logic
"""

from src.application.data_lake import data_lake
from src.domain import events
from src.domain.anomaly_detection import (
    ANOMALY_DEVIATION_TO_SENSOR_EVENT_TYPE_MAPPING,
    AnomalyDetection,
    AnomalyDetectionFlat,
    AnomalyDetectionRepository,
    AnomalyDetectionUncommited,
    services,
)
from src.domain.tsd import Tsd
from src.infrastructure.database import transaction
from src.infrastructure.errors import UnprocessableError


@transaction
async def get_historical_data(sensor_id: int) -> list[AnomalyDetection]:
    """Get the historical data."""

    return [
        instance
        async for instance in AnomalyDetectionRepository().by_sensor(sensor_id)
    ]


async def _create_sensor_event(
    schema: events.sensors.EventUncommited,
) -> events.sensors.Event:
    """Just encapsulate the logic of creating the sensor event."""

    repository = events.sensors.SensorsEventsRepository()

    event_flat: events.sensors.EventFlat = await repository.create(schema)
    return await repository.get(event_flat.id)


async def process():
    """Consume fetched data from data lake and detect the anomaly.
    The result is produced back to data lake and saved
    to the database for making the history available.
    """

    async for tsd in data_lake.time_series_data.consume():  # type is Tsd
        try:
            create_schema: AnomalyDetectionUncommited = (
                services.processing.dispatch(tsd)
            )
        except UnprocessableError:
            # NOTE: Skipped if matrix profile does not have enough values
            continue

        await _process(create_schema=create_schema, tsd=tsd)


@transaction
async def _process(create_schema: AnomalyDetectionUncommited, tsd: Tsd):
    # Save the anomaly detection to the database
    repository = AnomalyDetectionRepository()
    anomaly_detection_flat: AnomalyDetectionFlat = await repository.create(
        create_schema
    )
    anomaly_detection: AnomalyDetection = await repository.get(
        anomaly_detection_flat.id
    )

    # Handle the sensor event
    current_event_type: events.sensors.EventType = (
        ANOMALY_DEVIATION_TO_SENSOR_EVENT_TYPE_MAPPING[anomaly_detection.value]
    )

    if event_create_schema := await events.sensors.services.process(
        sensor_id=anomaly_detection.time_series_data.sensor_id,
        current_event_type=current_event_type,
    ):
        event: events.sensors.Event = await _create_sensor_event(
            event_create_schema
        )
        data_lake.events_by_sensor[
            anomaly_detection.time_series_data.sensor_id
        ].storage.append(event)

    # Update the data lake
    data_lake.anomaly_detections_for_simulation.storage.append(
        anomaly_detection
    )
    data_lake.anomaly_detections_by_sensor[tsd.sensor.id].storage.append(
        anomaly_detection
    )
