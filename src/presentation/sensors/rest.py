from functools import partial
from typing import AsyncGenerator

from fastapi import APIRouter, Request

from src.application import sensors, tsd
from src.domain.sensors import (
    Sensor,
    SensorBase,
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
async def template_sensors_list(
    _: Request, template_id: int
) -> ResponseMulti[SensorPublic]:
    """Return the list sensor for the specific template."""

    sensors: AsyncGenerator[Sensor, None] = SensorsRepository().by_template(
        template_id=template_id
    )
    sensors_public = [
        SensorPublic.from_orm(sensor) async for sensor in sensors
    ]

    return ResponseMulti[SensorPublic](result=sensors_public)


@router.get("/sensors")
@transaction
async def sensors_filter(
    _: Request, pinned: bool = False
) -> ResponseMulti[SensorPublic]:
    """Return the list of all sensors with possible filters.

    pinned -- the filter that goes through sensor configuration.
    """

    sensors: AsyncGenerator[Sensor, None] = SensorsRepository().filter(
        pinned=pinned
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
@transaction
async def sensor_update(
    _: Request, sensor_id: int, schema: SensorUpdateRequestBody
) -> Response[SensorPublic]:
    """Partially update the sensor."""

    sensor: Sensor = await services.crud.update(
        sensor_id=sensor_id,
        sensor_update_schema=SensorUpdatePartialSchema.from_orm(schema),
    )

    return Response[SensorPublic](result=SensorPublic.from_orm(sensor))


@router.delete("/sensors/{sensor_id}", status_code=204)
async def sensor_delete(_: Request, sensor_id: int) -> None:
    """Delete the sensor and its configuration.
    Stop the background tasks which process
    the time series data for that specific sensor.
    """

    # Remove the sensor and the configuration
    await sensors.delete(sensor_id)

    # Cancel the task if a user removes the sensor
    tasks.cancel(namespace="sensor_tsd_process", key=sensor_id)


@router.patch("/sensors/{sensor_id}/interactive-feedback-mode/toggle")
async def sensor_interactive_feedback_mode_toggle(
    _: Request, sensor_id: int
) -> Response[SensorPublic]:
    """Toggle the interactive feedback mode for the sensor.
    The mthod is PATCH since it is a partial update in the database.

    The mode could be turned on only after time series data collection.
    The number of time series data points should be greater
    than `window_size` global parameter (usually 288).
    """

    sensor: Sensor = await sensors.toggle_interactive_feedback_mode(
        sensor_id=sensor_id
    )

    return Response[SensorPublic](result=SensorPublic.from_orm(sensor))


@router.patch("/sensors/{sensor_id}/pin/toggle")
async def sensor_pin_toggle(
    _: Request, sensor_id: int
) -> Response[SensorPublic]:
    """Toggle the pin of the sensor on the dashboard.
    The mthod is PATCH since it is a partial update in the database.
    """

    sensor: Sensor = await sensors.toggle_pin(sensor_id=sensor_id)

    return Response[SensorPublic](result=SensorPublic.from_orm(sensor))
