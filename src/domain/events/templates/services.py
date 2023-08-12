from sqlalchemy import delete

from src.infrastructure.database import TemplatesEventsTable, transaction

from .models import Event, EventInDb, EventUncommited
from .repository import TemplatesEventsRepository


@transaction
async def delete_all():
    """This function is used by the startup hook if debug mode is on."""

    await TemplatesEventsRepository().execute(delete(TemplatesEventsTable))


@transaction
async def create(schema: EventUncommited) -> Event:
    """Create the database instance and return the reach datamodel."""

    repository = TemplatesEventsRepository()
    instance: EventInDb = await repository.create(schema)

    return await repository.get(instance.id)


@transaction
async def get_historical_data(template_id: int) -> list[Event]:
    """Get the historical data."""

    return [
        instance
        async for instance in TemplatesEventsRepository().by_template(
            template_id
        )
    ]
