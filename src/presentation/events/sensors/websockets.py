from contextlib import suppress

from fastapi import APIRouter, WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application.data_lake import data_lake
from src.domain.events.sensors import services as events_services
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.errors import NotFoundError

from .contracts import EventPublic

__all__ = ("router",)

router = APIRouter(prefix="/sensors")


@router.websocket("/{sensor_id}/events")
async def sensor_events(ws: WebSocket, sensor_id: int):
    await ws.accept()
    logger.success(
        "Opening WS connection for events fetching "
        f"from sensor: {sensor_id}"
    )

    # Just skip if there is no historical data in the database
    with suppress(NotFoundError):
        historical_data: list[EventPublic] = [
            EventPublic(
                id=instance.id,
                type=instance.type,
                sensor_id=instance.sensor.id,
            )
            for instance in (
                await events_services.get_historical_data(sensor_id)
            )
        ]

        # WARNING: The historical data should be sent by chanks since
        #           there is a HTTP protocol limitation on the data size
        # NOTE: Only last THREE elements are sent
        historical_response = ResponseMulti[EventPublic](
            result=historical_data[:3]
        )
        await ws.send_json(historical_response.encoded_dict())

    # Run the infinite consuming of new anomaly detection data
    async for instance in data_lake.sensors_events[sensor_id].consume():
        response = Response[EventPublic](
            result=EventPublic(
                id=instance.id,
                type=instance.type,
                sensor_id=instance.sensor.id,
            )
        )

        try:
            await ws.send_json(response.encoded_dict())
        except ConnectionClosed:
            logger.info(
                f"Websocket events connection closed for sensor: {sensor_id}"
            )
            break
