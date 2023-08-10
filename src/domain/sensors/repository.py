from typing import AsyncGenerator

from sqlalchemy import Result, Select, select
from sqlalchemy.orm import joinedload

from src.infrastructure.database import (
    BaseRepository,
    SensorsConfigurationsTable,
    SensorsTable,
)
from src.infrastructure.errors import NotFoundError
from src.infrastructure.errors.base import UnprocessableError

from .models import (
    Sensor,
    SensorConfigurationFlat,
    SensorConfigurationUncommited,
    SensorConfigurationUpdatePartialSchema,
    SensorInDb,
    SensorUncommited,
    SensorUpdatePartialSchema,
)

all = ("SensorsRepository", "SensorConfigurationRepository")


class SensorsConfigurationsRepository(
    BaseRepository[SensorsConfigurationsTable]
):
    schema_class = SensorsConfigurationsTable

    async def update_partially(
        self, id_: int, schema: SensorConfigurationUpdatePartialSchema
    ) -> SensorConfigurationFlat:
        if not (payload := schema.dict(exclude_none=True, exclude_unset=True)):
            raise UnprocessableError(
                message="Can not update without any payload"
            )

        _schema = await self._update(key="id", value=id_, payload=payload)

        return SensorConfigurationFlat.from_orm(_schema)

    async def update(
        self, id_: int, schema: SensorConfigurationUncommited
    ) -> SensorConfigurationFlat:
        """Update the configuration by id."""

        _schema = await self._update(
            key="id", value=id_, payload=schema.dict()
        )

        return SensorConfigurationFlat.from_orm(_schema)

    async def by_sensor(self, sensor_id: int) -> SensorConfigurationFlat:
        """Fetch the configuration by sensor id."""

        query: Select = (
            select(self.schema_class)
            .join(self.schema_class.sensor)
            .where(SensorsTable.id == sensor_id)
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return SensorConfigurationFlat.from_orm(schema)

    async def get(self, id_: int) -> SensorConfigurationFlat:
        """Fetch the configuration by id."""

        query: Select = select(self.schema_class).where(
            getattr(self.schema_class, "id") == id_
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return SensorConfigurationFlat.from_orm(schema)

    async def create(
        self, schema: SensorConfigurationUncommited
    ) -> SensorConfigurationFlat:
        """Create a new record in database."""

        _schema: SensorsConfigurationsTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return await self.get(id_=_schema.id)


class SensorsRepository(BaseRepository[SensorsTable]):
    schema_class = SensorsTable

    async def get(self, id_: int) -> Sensor:
        """Fetch the sensor by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(
                joinedload(self.schema_class.template),
                joinedload(self.schema_class.configuration),
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

    async def update_partially(
        self, id_: int, schema: SensorUpdatePartialSchema
    ) -> SensorInDb:
        if not (payload := schema.dict(exclude_none=True, exclude_unset=True)):
            raise UnprocessableError(
                message="Can not update without any payload"
            )

        _schema = await self._update(key="id", value=id_, payload=payload)

        return SensorInDb.from_orm(_schema)

    async def all(self) -> AsyncGenerator[Sensor, None]:
        """Fetch all sensors from database."""

        result: Result = await self.execute(
            select(self.schema_class).options(
                joinedload(self.schema_class.template),
                joinedload(self.schema_class.configuration),
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
                joinedload(self.schema_class.configuration),
            )
        )
        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield Sensor.from_orm(schema)
