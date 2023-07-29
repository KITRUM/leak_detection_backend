"""This module takes over setting up the communication between
application domains in order to provide the high-level feature
called `ANOMALY DETECTION`.

It depends on:
    - the time series data that is fetched from the external source,
    - platforms
    - anomaly deviation calculation logic
"""

from loguru import logger

from src.application.data_lake import data_lake
from src.domain.anomaly_detection import (
    AnomalyDetection,
    AnomalyDetectionUncommited,
    services,
)


async def process():
    """Consume fetched data from data lake and detect the anomaly.
    The result is produced back to data lake and saved
    to the database for making the history available.
    """

    async for tsd in data_lake.time_series_data.consume():  # type is Tsd
        logger.debug(f"Anomaly detection processing: {tsd.id}")
        create_schema: AnomalyDetectionUncommited = services.process(tsd)

        # Save a detection to the database
        anomaly_detection: AnomalyDetection = (
            await services.save_anomaly_detection(create_schema)
        )

        # Update the data lake
        data_lake.anomaly_detections.storage.append(anomaly_detection)
        data_lake.anomaly_detections_by_sensor[tsd.sensor.id].storage.append(
            anomaly_detection
        )
