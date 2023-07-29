from fastapi import APIRouter, WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application.data_lake import data_lake
from src.domain.tsd import services as tsd_services
from src.infrastructure.contracts import Response, ResponseMulti

from .contracts import TsdPublic

__all__ = ("router",)

router = APIRouter(prefix="/sensors", tags=["Time series data"])


@router.websocket("/{sensor_id}/time-series-data")
async def time_series_data(ws: WebSocket, sensor_id: int):
    """Establish the websocket connection and send the next data:
    1. historical time series data
    2. the new time series data on each event that produced by daemon

    This information is taken per sensor.
    """

    await ws.accept()
    logger.success(
        "Opening WS connection for Estimation results fetching "
        f"from sensor: {sensor_id}"
    )

    historical_tsd_set: list[TsdPublic] = [
        TsdPublic.from_orm(instance)
        for instance in (await tsd_services.get_historical_data(sensor_id))
    ]

    # WARNING: The historical data should be sent by chanks since
    #           there is a HTTP protocol limitation on the data size
    historical_response = ResponseMulti[TsdPublic](result=historical_tsd_set)
    await ws.send_json(historical_response.encoded_dict())

    async for tsd in data_lake.time_series_data_by_sensor[sensor_id].consume():
        response = Response[TsdPublic](result=TsdPublic.from_orm(tsd))

        try:
            await ws.send_json(response.encoded_dict())
        except ConnectionClosed:
            logger.info(f"Websocket connection closed for sensor: {sensor_id}")
            break
