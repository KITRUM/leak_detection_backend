import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request, status

from src.application import tsd
from src.domain.sensors import Sensor, SensorsRepository
from src.domain.sensors import services as sensors_services
from src.domain.sensors.models import (
    SensorBase,
    SensorConfigurationUncommited,
    SensorCreateSchema,
)
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.database import transaction
from src.presentation.sensors.contracts import (
    SensorCreateRequestBody,
    SensorPublic,
)

__all__ = ("router",)

router = APIRouter(prefix="", tags=["Sensors"])


@router.post(
    "/templates/{template_id}/sensors", status_code=status.HTTP_201_CREATED
)
@transaction
async def sensor_create(
    _: Request, template_id: int, schema: SensorCreateRequestBody
) -> Response[SensorPublic]:
    """Return the list of platforms that are provided."""

    # Save sesor and configuration to the database
    create_schema = SensorCreateSchema(
        configuration_uncommited=SensorConfigurationUncommited(),
        template_id=template_id,
        sensor_payload=SensorBase.from_orm(schema),
    )
    sensor: Sensor = await sensors_services.create(create_schema)

    # Run the processing task in a background on sensor creation
    asyncio.create_task(tsd.process(sensor))

    return Response[SensorPublic](result=SensorPublic.from_orm(sensor))


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
