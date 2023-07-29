from contextlib import suppress

from fastapi import APIRouter, WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application.data_lake import data_lake
from src.domain.estimation import services as estimation_services
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.errors.base import NotFoundError

from .contracts import EstimationSummaryPublic

__all__ = ("router",)

router = APIRouter(prefix="/sensors", tags=["Estimation"])


@router.websocket("/{sensor_id}/estimation")
async def estimation_summary(ws: WebSocket, sensor_id: int):
    """Establish the websocket connection and send the next data:
    1. historical estimation data
    2. the new estimation summaries data on each event that produced

    This information is taken per sensor.

    WARNING: this feature is quite dangerous since there is no
        domain expert to finish it completely.
        Might works unexpected.
    """

    await ws.accept()
    logger.success(
        "Opening WS connection for Estimation results fetching "
        f"from sensor: {sensor_id}"
    )

    # Just skip if there is no historical data in the database
    with suppress(NotFoundError):
        historical_data: list[EstimationSummaryPublic] = [
            EstimationSummaryPublic.from_orm(instance)
            for instance in (
                await estimation_services.get_historical_data(sensor_id)
            )
        ]

        # WARNING: The historical data should be sent by chanks since
        #           there is a HTTP protocol limitation on the data size
        historical_response = ResponseMulti[EstimationSummaryPublic](
            result=historical_data
        )
        await ws.send_json(historical_response.encoded_dict())

    # Run the infinite consuming of new anomaly detection data
    leak_storage = data_lake.anomaly_detections_by_sensor[sensor_id]
    async for instance in leak_storage.consume():
        response = Response[EstimationSummaryPublic](
            result=EstimationSummaryPublic.from_orm(instance)
        )

        try:
            await ws.send_json(response.encoded_dict())
        except ConnectionClosed:
            logger.info(f"Websocket connection closed for sensor: {sensor_id}")
            break
