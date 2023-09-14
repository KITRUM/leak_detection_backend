from src.domain.events import sensors
from src.infrastructure.database import transaction

__all__ = ("get_last",)


@transaction
async def get_last(sensor_id: int) -> sensors.EventFlat:
    """Get the last item."""

    return await sensors.SensorsEventsRepository().last(sensor_id)
