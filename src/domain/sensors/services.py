from typing import Any

from src.infrastructure.database.services.transaction import transaction

from .models import (
    Sensor,
    SensorConfigurationInDb,
    SensorCreateSchema,
    SensorUncommited,
)
from .repository import SensorsConfigurationsRepository, SensorsRepository


@transaction
async def create(schema: SensorCreateSchema) -> Sensor:
    """Create a sensor configuration and the sensor attached."""

    sensors_repository = SensorsRepository()
    configurations_repository = SensorsConfigurationsRepository()

    configuration: SensorConfigurationInDb = (
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
