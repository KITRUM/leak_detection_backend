from contextlib import suppress

from fastapi import APIRouter, WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application import events
from src.application.data_lake import data_lake
from src.domain.events.sensors import EventFlat
from src.infrastructure.contracts import Response
from src.infrastructure.errors import NotFoundError

from .contracts import EventPublic

__all__ = ("router",)

router = APIRouter(prefix="/events/sensors")


@router.websocket("/{sensor_id}")
async def sensor_events(ws: WebSocket, sensor_id: int):
    await ws.accept()
    logger.success(
        "Opening WS connection for events fetching "
        f"from sensor: {sensor_id}"
    )

    # Just skip if there is no historical data in the database
    with suppress(NotFoundError):
        event_flat: EventFlat = await events.sensors.get_last(sensor_id)
        event_public = EventPublic(
            id=event_flat.id,
            type=event_flat.type,
            sensor_id=event_flat.sensor_id,
        )
        response = Response[EventPublic](result=event_public)
        await ws.send_json(response.encoded_dict())

    # Run the infinite consuming of new sensor events
    async for instance in data_lake.events_by_sensor[sensor_id].consume():
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
