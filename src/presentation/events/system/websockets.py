from fastapi import APIRouter, WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application.data_lake import data_lake
from src.infrastructure.contracts import Response

from .contracts import EventPublic

__all__ = ("router",)

router = APIRouter(prefix="/events/system")


@router.websocket("")
async def system_events(ws: WebSocket):
    await ws.accept()
    logger.success("Opening WS connection for system events fetching.")

    # Run the infinite consuming of new system events
    async for instance in data_lake.events_system.consume():
        response = Response[EventPublic](result=EventPublic.from_orm(instance))

        try:
            await ws.send_json(response.encoded_dict())
        except ConnectionClosed:
            logger.info(
                "Websocket events connection closed for system events fetching"
            )
            break
