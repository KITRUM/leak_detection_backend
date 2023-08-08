from typing import Any

from src.infrastructure.database.services.transaction import transaction

from .models import (
    Sensor,
    SensorConfigurationFlat,
    SensorConfigurationPartialUpdateSchema,
    SensorCreateSchema,
    SensorUncommited,
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
async def update_configuration(
    sensor_id: int, update_schema: SensorConfigurationPartialUpdateSchema
) -> SensorConfigurationFlat:
    """Update the sensor's configuration."""

    sensor = await SensorsRepository().get(id_=sensor_id)

    return await SensorsConfigurationsRepository().update_partially(
        sensor.configuration.id, update_schema
    )
