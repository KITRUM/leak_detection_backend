from typing import AsyncGenerator

from sqlalchemy import Result, Select, select
from sqlalchemy.orm import joinedload

from src.infrastructure.database import BaseRepository, TemplatesEventsTable
from src.infrastructure.errors import NotFoundError

from .models import Event, EventInDb, EventUncommited

all = ("SensorsEventsRepository",)


class TemplatesEventsRepository(BaseRepository[TemplatesEventsTable]):
    schema_class = TemplatesEventsTable

    async def get(self, id_: int) -> Event:
        """Fetch the instance by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(joinedload(self.schema_class.template))
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return Event.from_orm(schema)

    async def create(self, schema: EventUncommited) -> EventInDb:
        """Create a new record in database."""

        _schema: TemplatesEventsTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return EventInDb.from_orm(_schema)

    async def by_template(
        self, template_id: int
    ) -> AsyncGenerator[Event, None]:
        """Fetch all anomaly detections for the template."""

        query: Select = (
            select(self.schema_class)
            .options(
                joinedload(self.schema_class.template),
            )
            .where(getattr(self.schema_class, "template_id") == template_id)
        )

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield Event.from_orm(schema)
