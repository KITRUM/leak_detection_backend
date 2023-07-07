import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request, status

from src.application import tsd
from src.application.database import transaction
from src.domain.sensors import (
    Sensor,
    SensorCreateRequestBody,
    SensorPublic,
    SensorsRepository,
    SensorUncommited,
)
from src.infrastructure.models import Response, ResponseMulti

router = APIRouter(prefix="", tags=["Sensors"])


@router.post(
    "/templates/{template_id}/sensors", status_code=status.HTTP_201_CREATED
)
@transaction
async def sensor_create(
    _: Request, template_id: int, schema: SensorCreateRequestBody
) -> Response[SensorPublic]:
    """Return the list of platforms that are provided."""

    # Save sesor to the database
    create_payload = schema.dict() | {"template_id": template_id}
    create_schema = SensorUncommited(**create_payload)  # type: ignore
    sensor: Sensor = await SensorsRepository().create(create_schema)

    # Run the task in a background
    asyncio.create_task(tsd.process(sensor))

    sensor_public = SensorPublic.from_orm(sensor)

    return Response[SensorPublic](result=sensor_public)


@router.get("/templates/{template_id}/sensors")
@transaction
async def sensors_list(
    _: Request, template_id: int
) -> ResponseMulti[SensorPublic]:
    """Return the list of platforms that are provided."""

    sensors: AsyncGenerator[Sensor, None] = SensorsRepository().by_template(
        template_id
    )
    sensors_public = [
        SensorPublic.from_orm(sensor) async for sensor in sensors
    ]

    return ResponseMulti[SensorPublic](result=sensors_public)


@router.get("/sensors/{sensor_id}")
@transaction
async def sensor_retrieve(_: Request, sensor_id: int):
    """Return the list of sensors within the sensor."""

    sensor: Sensor = await SensorsRepository().get(sensor_id)
    sensor_public = SensorPublic.from_orm(sensor)

    return Response[SensorPublic](result=sensor_public)
