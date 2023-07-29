from contextlib import suppress

from fastapi import APIRouter, WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application.data_lake import data_lake
from src.domain.anomaly_detection import services as anomaly_detection_services
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.errors import NotFoundError
from src.presentation.anomaly_detection.contracts import AnomalyDetectionPublic

__all__ = ("router",)

router = APIRouter(prefix="/sensors", tags=["Anomaly detections"])


@router.websocket("/{sensor_id}/anomaly-detections")
async def anomaly_detections(ws: WebSocket, sensor_id: int):
    await ws.accept()
    logger.success(
        "Opening WS connection for Anomaly detections fetching "
        f"from sensor: {sensor_id}"
    )

    # Just skip if there is no historical data in the database
    with suppress(NotFoundError):
        historical_data: list[AnomalyDetectionPublic] = [
            AnomalyDetectionPublic.from_orm(instance)
            for instance in (
                await anomaly_detection_services.get_historical_data(sensor_id)
            )
        ]

        # WARNING: The historical data should be sent by chanks since
        #           there is a HTTP protocol limitation on the data size
        historical_response = ResponseMulti[AnomalyDetectionPublic](
            result=historical_data
        )
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
