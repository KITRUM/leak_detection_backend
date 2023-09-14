from contextlib import suppress

from fastapi import WebSocket
from loguru import logger
from websockets.exceptions import ConnectionClosed

from src.application.data_lake import data_lake
from src.domain.events.templates import services
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.errors import NotFoundError

from .._router import router
from .contracts import EventPublic


@router.websocket("/templates/{template_id}")
async def sensor_events(ws: WebSocket, template_id: int):
    await ws.accept()
    logger.success(
        "Opening WS connection for events fetching "
        f"from template: {template_id}"
    )

    # Just skip if there is no historical data in the database
    with suppress(NotFoundError):
        historical_data: list[EventPublic] = [
            EventPublic(
                id=instance.id,
                type=instance.type,
                template_id=instance.template.id,
            )
            for instance in (
                await services.crud.get_historical_data(template_id)
            )
        ]

        # WARNING: The historical data should be sent by chanks since
        #           there is a HTTP protocol limitation on the data size
        # NOTE: Only last THREE elements are sent
        historical_response = ResponseMulti[EventPublic](
            result=historical_data[:3]
        )
        await ws.send_json(historical_response.encoded_dict())

    # Run the infinite consuming of new template events
    async for instance in data_lake.events_by_template[template_id].consume():
        response = Response[EventPublic](
            result=EventPublic(
                id=instance.id,
                type=instance.type,
                template_id=instance.template.id,
            )
        )

        try:
            await ws.send_json(response.encoded_dict())
        except ConnectionClosed:
            logger.info(
                f"Websocket events connection closed for sensor: {template_id}"
            )
            break
