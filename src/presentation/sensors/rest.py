from functools import partial
from typing import AsyncGenerator

from fastapi import APIRouter, Request

from src.application import sensors, tsd
from src.domain.sensors import (
    Sensor,
    SensorBase,
    SensorConfigurationUpdatePartialSchema,
    SensorsRepository,
    SensorUpdatePartialSchema,
    services,
)
from src.infrastructure.application import tasks
from src.infrastructure.contracts import Response, ResponseMulti
from src.infrastructure.database import transaction

from .contracts import (
    SensorCreateRequestBody,
    SensorPublic,
    SensorUpdateRequestBody,
)

__all__ = ("router",)

router = APIRouter(prefix="", tags=["Sensors"])


# ************************************************
# ********** CRUD block **********
# ************************************************
@router.post("/templates/{template_id}/sensors", status_code=201)
async def sensor_create(
    _: Request, template_id: int, schema: SensorCreateRequestBody
) -> Response[SensorPublic]:
    """Return the list of platforms that are provided."""

    sensor: Sensor = await sensors.create(
        template_id=template_id, sensor_payload=SensorBase.from_orm(schema)
    )

    # Run the processing task in a background on sensor creation
    await tasks.run(
        namespace="sensor_tsd_process",
        key=sensor.id,
        coro=partial(tsd.process, sensor),
    )

    return Response[SensorPublic](result=SensorPublic.from_orm(sensor))


@router.get("/templates/{template_id}/sensors")
@transaction
async def sensors_list(
    _: Request, template_id: int, pinned: bool | None = None
) -> ResponseMulti[SensorPublic]:
    """Return the list of platforms that are provided."""

    sensors: AsyncGenerator[Sensor, None] = SensorsRepository().by_template(
        template_id=template_id, pinned=pinned
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


@router.patch("/sensors/{sensor_id}")
async def sensor_update(
    _: Request, sensor_id: int, schema: SensorUpdateRequestBody
) -> Response[SensorPublic]:
    """Partially update the sensor."""

    sensor: Sensor = await services.crud.update(
        sensor_id=sensor_id,
        sensor_update_schema=SensorUpdatePartialSchema.from_orm(schema),
        configuration_update_schema=SensorConfigurationUpdatePartialSchema.from_orm(
            schema.configuration
        ),
    )

    return Response[SensorPublic](result=SensorPublic.from_orm(sensor))


@router.delete("/sensors/{sensor_id}", status_code=204)
async def sensor_delete(_: Request, sensor_id: int) -> None:
    """Delete the sensor and its configuration.
    Stop the background tasks which process
    the time series data for that specific sensor.
    """

    # Remove the sensor and the configuration
    await services.crud.delete(sensor_id)

    # Cancel the task if a user removes the sensor
    tasks.cancel(namespace="sensor_tsd_process", key=sensor_id)

    await services.crud.delete(sensor_id)
