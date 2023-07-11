from contextlib import suppress

from fastapi import APIRouter, WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application.data_lake import data_lake
from src.domain.anomaly_detection import AnomalyDetectionRepository
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.errors import NotFoundError
from src.presentation.anomaly_detection.contracts import AnomalyDetectionPublic

__all__ = ("router",)

router = APIRouter(prefix="/sensors", tags=["Anomaly detections"])


async def get_historical_data_response(
    sensor_id: int,
) -> ResponseMulti[AnomalyDetectionPublic]:
    # Get the historical data and convert to the public model
    historical_data: list[AnomalyDetectionPublic] = [
        AnomalyDetectionPublic.from_orm(instance)
        async for instance in AnomalyDetectionRepository().by_sensor(sensor_id)
    ]

    # WARNING: The historical data should be sent by chanks since
    #           there is a HTTP protocol limitation on the data size
    return ResponseMulti[AnomalyDetectionPublic](result=historical_data)


@router.websocket("/{sensor_id}/anomaly-detections")
async def anomaly_detections(ws: WebSocket, sensor_id: int):
    await ws.accept()
    logger.success(
        f"Opening WS connection for Anomaly detections fetching from sensor: {sensor_id}"
    )

    # Just skip if there is no historical data in the database
    with suppress(NotFoundError):
        historical_response: ResponseMulti[
            AnomalyDetectionPublic
        ] = await get_historical_data_response(sensor_id)
        await ws.send_json(historical_response.encoded_dict())

    # Run the infinite consuming of new anomaly detection data
    leak_storage = data_lake.anomaly_detections_by_sensor[sensor_id]
    async for instance in leak_storage.consume():
        response = Response[AnomalyDetectionPublic](
            result=AnomalyDetectionPublic.from_orm(instance)
        )

        try:
            await ws.send_json(response.encoded_dict())
        except ConnectionClosed:
            logger.info(f"Websocket connection closed for sensor: {sensor_id}")
            break
