from typing import AsyncGenerator

from sqlalchemy import Result, Select, desc, select

from src.infrastructure.database import BaseRepository, SystemEventsTable
from src.infrastructure.errors import NotFoundError

from .models import Event, EventType, EventUncommited

all = ("SystemEventsRepository",)


class SystemEventsRepository(BaseRepository[SystemEventsTable]):
    schema_class = SystemEventsTable

    async def get(self, id_: int) -> Event:
        """Fetch the instance by id."""

        query: Select = select(self.schema_class).where(
            getattr(self.schema_class, "id") == id_
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return Event.from_orm(schema)

    async def create(self, schema: EventUncommited) -> Event:
        """Create a new record in database."""

        _schema: SystemEventsTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return Event.from_orm(_schema)

    async def filter(
        self,
        limit: int | None = None,
        exclude_types: tuple[EventType] | None = None,
    ) -> AsyncGenerator[Event, None]:
        """Filter events by some properties."""

        query: Select = select(self.schema_class)

        # Exclude some types of events
        if exclude_types is not None:
            query = query.where(
                getattr(self.schema_class, "type").not_(exclude_types)
            )

        # Limit the number of records
        if limit is not None:
            query = query.limit(limit)

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield Event.from_orm(schema)

    async def last(self) -> Event:
        """Get the last event from the database."""

        query: Select = (
            select(self.schema_class)
            .order_by(desc(self.schema_class.id))
            .limit(1)
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return Event.from_orm(schema)
