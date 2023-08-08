import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request, status

from src.application import tsd
from src.domain.sensors import (
    Sensor,
    SensorBase,
    SensorConfigurationUncommited,
    SensorCreateSchema,
    SensorsRepository,
)
from src.domain.sensors import services as sensors_services
from src.domain.sensors.models import (
    SensorConfigurationFlat,
    SensorConfigurationPartialUpdateSchema,
)
from src.domain.sensors.repository import SensorsConfigurationsRepository
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.database import transaction

from .contracts import (
    SensorConfigurationPublic,
    SensorConfigurationUpdateRequestBody,
    SensorCreateRequestBody,
    SensorPublic,
)

__all__ = ("router",)

router = APIRouter(prefix="", tags=["Sensors"])


# ************************************************
# ********** CRUD block **********
# ************************************************
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


# ************************************************
# ********** Interactive feedback mode ***********
# ************************************************
@router.get("/sensors/{sensor_id}/configuration")
@transaction
async def sensor_configuration_retrieve(
    _: Request, sensor_id: int
) -> Response[SensorConfigurationPublic]:
    """Return the sensor's configuration."""

    configuration: SensorConfigurationFlat = (
        await SensorsConfigurationsRepository().by_sensor(sensor_id)
    )
    configuration_public = SensorConfigurationPublic.from_orm(configuration)

    return Response[SensorConfigurationPublic](result=configuration_public)


@router.patch("/sensors/{sensor_id}/configuration")
async def sensor_configuration_update(
    _: Request, sensor_id: int, schema: SensorConfigurationUpdateRequestBody
) -> Response[SensorConfigurationPublic]:
    """Partially update the sensor's configuration."""

    configuration: SensorConfigurationFlat = (
        await sensors_services.update_configuration(
            sensor_id,
            SensorConfigurationPartialUpdateSchema.from_orm(schema),
        )
    )

    return Response[SensorConfigurationPublic](
        result=SensorConfigurationPublic.from_orm(configuration)
    )
