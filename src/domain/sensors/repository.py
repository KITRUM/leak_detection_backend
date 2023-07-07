from typing import AsyncGenerator

from sqlalchemy import Result, Select, select
from sqlalchemy.orm import joinedload

from src.domain.sensors.models import Sensor, SensorUncommited
from src.infrastructure.database import BaseRepository, SensorsTable
from src.infrastructure.errors import NotFoundError

all = ("SensorsRepository",)


class SensorsRepository(BaseRepository[SensorsTable]):
    schema_class = SensorsTable

    async def get(self, id_: int) -> Sensor:
        """Fetch the sensor by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(
                joinedload(self.schema_class.template),
            )
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return Sensor.from_orm(schema)

    async def create(self, schema: SensorUncommited) -> Sensor:
        """Create a new record in database."""

        _schema: SensorsTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return await self.get(id_=_schema.id)

    async def all(self) -> AsyncGenerator[Sensor, None]:
        """Fetch all sensors from database."""

        result: Result = await self.execute(
            select(self.schema_class).options(
                joinedload(self.schema_class.template)
            )
        )
        schemas = result.scalars().all()

        for schema in schemas:
            yield Sensor.from_orm(schema)

    async def by_template(
        self, template_id: int
    ) -> AsyncGenerator[Sensor, None]:
        """Fetch all sensors by template from database.
        The template table is joined.
        """

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "template_id") == template_id)
            .options(
                joinedload(self.schema_class.template),
            )
        )
        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield Sensor.from_orm(schema)
