from contextlib import suppress
from typing import Any

from src.infrastructure.database import transaction
from src.infrastructure.errors import UnprocessableError

from .models import (
    Sensor,
    SensorConfigurationFlat,
    SensorConfigurationUpdatePartialSchema,
    SensorCreateSchema,
    SensorUncommited,
    SensorUpdatePartialSchema,
)
from .repository import SensorsConfigurationsRepository, SensorsRepository


@transaction
async def create(schema: SensorCreateSchema) -> Sensor:
    """Create a sensor configuration and the sensor attached."""

    sensors_repository = SensorsRepository()
    configurations_repository = SensorsConfigurationsRepository()

    configuration: SensorConfigurationFlat = (
        await configurations_repository.create(schema.configuration_uncommited)
    )

    _sensor_uncommited_payload: dict[
        str, Any
    ] = schema.sensor_payload.dict() | {
        "template_id": schema.template_id,
        "configuration_id": configuration.id,
    }
    sensor: Sensor = await sensors_repository.create(
        SensorUncommited(**_sensor_uncommited_payload)
    )

    return sensor


@transaction
async def update(
    sensor_id: int,
    sensor_update_schema: SensorUpdatePartialSchema,
    configuration_update_schema: SensorConfigurationUpdatePartialSchema,
) -> Sensor:
    """Update the sensor and the configuration in one transaction hop."""

    # PERF: Abusing the database. (not critical for now)

    sensor_repository = SensorsRepository()
    sensor: Sensor = await sensor_repository.get(id_=sensor_id)

    # Update the configuration if defined
    with suppress(UnprocessableError):
        await SensorsConfigurationsRepository().update_partially(
            id_=sensor.configuration.id, schema=configuration_update_schema
        )

    # Update the sensor's payload if defined
    with suppress(UnprocessableError):
        await sensor_repository.update_partially(
            id_=sensor.id, schema=sensor_update_schema
        )

    return await sensor_repository.get(id_=sensor_id)


@transaction
async def delete(sensor_id: int) -> None:
    """Delete the sensor and its configuration."""

    # PERF: Abusing the database. (not critical for now)

    sensor_repository = SensorsRepository()
    sensor: Sensor = await sensor_repository.get(id_=sensor_id)

    await SensorsConfigurationsRepository().delete(sensor.configuration.id)
    await sensor_repository.delete(sensor.id)
