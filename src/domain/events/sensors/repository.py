from typing import AsyncGenerator

from sqlalchemy import Result, Select, select
from sqlalchemy.orm import joinedload

from src.infrastructure.database import BaseRepository, SensorsEventsTable
from src.infrastructure.errors import NotFoundError

from .models import Event, EventFlat, EventUncommited

all = ("SensorsEventsRepository",)


class SensorsEventsRepository(BaseRepository[SensorsEventsTable]):
    schema_class = SensorsEventsTable

    async def get(self, id_: int) -> Event:
        """Fetch the instance by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(joinedload(self.schema_class.sensor))
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return Event.from_orm(schema)

    async def create(self, schema: EventUncommited) -> EventFlat:
        """Create a new record in database."""

        _schema: SensorsEventsTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return EventFlat.from_orm(_schema)

    async def by_sensor(self, sensor_id: int) -> AsyncGenerator[Event, None]:
        """Fetch all anomaly detections for the sensor."""

        query: Select = (
            select(self.schema_class)
            .options(
                joinedload(self.schema_class.sensor),
            )
            .where(getattr(self.schema_class, "sensor_id") == sensor_id)
        )

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield Event.from_orm(schema)
