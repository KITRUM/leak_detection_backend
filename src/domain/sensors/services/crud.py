from contextlib import suppress
from typing import Any, AsyncGenerator

from src.infrastructure.database import transaction
from src.infrastructure.errors import UnprocessableError

from ..models import (
    Sensor,
    SensorConfigurationFlat,
    SensorCreateSchema,
    SensorUncommited,
    SensorUpdatePartialSchema,
)
from ..repository import SensorsConfigurationsRepository, SensorsRepository


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


async def update(
    sensor_id: int,
    sensor_update_schema: SensorUpdatePartialSchema = (
        SensorUpdatePartialSchema()
    ),
) -> Sensor:
    """Update the sensor and the configuration in one transaction hop."""

    # PERF: Abusing the database. (not critical for now)

    sensor_repository = SensorsRepository()
    sensor: Sensor = await sensor_repository.get(id_=sensor_id)

    # Update the sensor's payload if defined
    with suppress(UnprocessableError):
        await sensor_repository.update_partially(
            id_=sensor.id, schema=sensor_update_schema
        )

    return await sensor_repository.get(id_=sensor_id)
