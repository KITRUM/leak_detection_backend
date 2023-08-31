"""
This module takes over setting up the communication between
application domains in order to provide the high-level feature
called `ANOMALY DETECTION`.

It depends on:
    - the time series data that is fetched from the external source,
    - platforms
    - anomaly deviation calculation logic
"""

from src.application.data_lake import data_lake
from src.domain.anomaly_detection import (
    AnomalyDetection,
    AnomalyDetectionUncommited,
)
from src.domain.anomaly_detection import services as anomaly_detection_services
from src.infrastructure.errors import UnprocessableError


async def process():
    """Consume fetched data from data lake and detect the anomaly.
    The result is produced back to data lake and saved
    to the database for making the history available.
    """

    async for tsd in data_lake.time_series_data.consume():  # type is Tsd
        try:
            create_schema: AnomalyDetectionUncommited = (
                anomaly_detection_services.processing.dispatch(tsd)
            )
        except UnprocessableError:
            # NOTE: Skipped if matrix profile does not have enough values
            continue

        # Save a detection to the database
        anomaly_detection: AnomalyDetection = (
            await anomaly_detection_services.crud.create(create_schema)
        )

        # Update the data lake
        data_lake.anomaly_detections_for_simulation.storage.append(
            anomaly_detection
        )
        data_lake.anomaly_detections_for_events.storage.append(
            anomaly_detection
        )
        data_lake.anomaly_detections_by_sensor[tsd.sensor.id].storage.append(
            anomaly_detection
        )
