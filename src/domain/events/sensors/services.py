from sqlalchemy import delete

from src.infrastructure.database import SensorsEventsTable
from src.infrastructure.database.services.transaction import transaction

from .models import Event, EventInDb, EventUncommited
from .repository import SensorsEventsRepository


@transaction
async def delete_all():
    """This function is used by the startup hook if debug mode is on."""

    await SensorsEventsRepository().execute(delete(SensorsEventsTable))


@transaction
async def create(schema: EventUncommited) -> Event:
    """Create the database instance and return the reach datamodel."""

    repository = SensorsEventsRepository()
    instance: EventInDb = await repository.create(schema)

    return await repository.get(instance.id)


@transaction
async def get_historical_data(
    sensor_id: int,
) -> list[Event]:
    """Get the historical data."""

    return [
        instance
        async for instance in SensorsEventsRepository().by_sensor(sensor_id)
    ]
