from loguru import logger

from src.application.data_lake import data_lake

from .sensors import process as sensor_event_processing
from .templates import process as template_event_processing

all = ("process",)


async def process():
    """This function represents the engine of producing events
    that are related to the specific template and its sensors.

    First of all the sensor's event processes and in case of its
    existence the template event processing starts.

    🚧 Currently, it is based on the anomaly detection results.
       Might be that it should be changed to the Estimation results.
    """

    data_lake_items = data_lake.anomaly_detections_for_events

    async for anomaly_detection in data_lake_items.consume():
        logger.debug(
            "Processing the event for anomaly detection: "
            f"{anomaly_detection.id}"
        )
        if event := (await sensor_event_processing(anomaly_detection)):
            logger.success(f"Processing the sensor event: {event.id}")

            await template_event_processing(event)