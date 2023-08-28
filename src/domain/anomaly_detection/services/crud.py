from src.infrastructure.database import transaction

from ..models import AnomalyDetection, AnomalyDetectionUncommited
from ..repository import AnomalyDetectionRepository

__all__ = ("create", "get_historical_data")


@transaction
async def create(schema: AnomalyDetectionUncommited) -> AnomalyDetection:
    repository = AnomalyDetectionRepository()
    instance = await repository.create(schema)

    return await repository.get(instance.id)


@transaction
async def get_historical_data(
    sensor_id: int,
) -> list[AnomalyDetection]:
    """Get the historical data."""

    return [
        instance
        async for instance in AnomalyDetectionRepository().by_sensor(sensor_id)
    ]
