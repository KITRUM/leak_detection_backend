from src.infrastructure.database.services.transaction import transaction

from ..models import Event, EventFlat, EventUncommited
from ..repository import TemplatesEventsRepository

__all__ = ("create", "get_historical_data")


@transaction
async def create(schema: EventUncommited) -> Event:
    """Create the database instance and return the reach datamodel."""

    repository = TemplatesEventsRepository()
    instance: EventFlat = await repository.create(schema)

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
