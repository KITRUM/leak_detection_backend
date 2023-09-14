from src.infrastructure.database import transaction

from ..models import Event, EventUncommited
from ..repository import SystemEventsRepository

__all__ = ("create", "last")


@transaction
async def create(schema: EventUncommited) -> Event:
    """Create a new record in database."""

    return await SystemEventsRepository().create(schema)


@transaction
async def last(number: int = 10) -> list[Event]:
    """Fetch the last number of events.
    By default, fetches the last 10 events.
    """

    return [
        item async for item in SystemEventsRepository().filter(limit=number)
    ]
