from loguru import logger

from src.application.data_lake import data_lake

from . import sensors as sensor_events

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
        if event := (await sensor_events.process(anomaly_detection)):
            logger.success(f"Processing the sensor event: {event.type}")

            # Update the data lake
            data_lake.events_by_sensor[
                anomaly_detection.time_series_data.sensor_id
            ].storage.append(event)

            # Template events processing
            # await template_event_processing(event)
