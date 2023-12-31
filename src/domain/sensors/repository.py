from typing import AsyncGenerator

from sqlalchemy import Result, Select, func, select
from sqlalchemy.orm import joinedload

from src.infrastructure.database import (
    BaseRepository,
    SensorsConfigurationsTable,
    SensorsTable,
    TimeSeriesDataTable,
)
from src.infrastructure.errors import NotFoundError, UnprocessableError

from .models import (
    Sensor,
    SensorConfigurationFlat,
    SensorConfigurationUncommited,
    SensorConfigurationUpdatePartialSchema,
    SensorFlat,
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
    ) -> SensorFlat:
        if not (payload := schema.dict(exclude_none=True, exclude_unset=True)):
            raise UnprocessableError(
                message="Can not update without any payload"
            )

        _schema = await self._update(key="id", value=id_, payload=payload)

        return SensorFlat.from_orm(_schema)

    async def all(self) -> AsyncGenerator[Sensor, None]:
        """Fetch all sensors from database."""

        result: Result = await self._session.execute(
            select(self.schema_class).options(
                joinedload(self.schema_class.template),
                joinedload(self.schema_class.configuration),
            )
        )
        schemas = result.scalars().all()

        for schema in schemas:
            yield Sensor.from_orm(schema)

    async def filter(
        self, pinned: bool | None = None
    ) -> AsyncGenerator[Sensor, None]:
        """Select with high level filters."""

        # TODO: Add the template here and create the uniform interface

        filters = []

        if pinned is not None:
            filters.append(SensorsConfigurationsTable.pinned == pinned)

        result: Result = await self._session.execute(
            select(self.schema_class)
            .join(self.schema_class.configuration)
            .options(
                joinedload(self.schema_class.template),
                joinedload(self.schema_class.configuration),
            )
            .where(*filters)  # type: ignore[arg-type]
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

        result: Result = await self._session.execute(
            select(self.schema_class)
            .options(
                joinedload(self.schema_class.template),
                joinedload(self.schema_class.configuration),
            )
            .where(
                getattr(self.schema_class, "template_id") == template_id,
            )
        )

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield Sensor.from_orm(schema)

    async def tsd_count(self, sensor_id: int) -> int:
        """Return the number of time series data items by sensor."""

        result: Result = await self.execute(
            select(func.count(TimeSeriesDataTable.id)).where(
                getattr(TimeSeriesDataTable, "sensor_id") == sensor_id
            )
        )
        value = result.scalar()

        if not isinstance(value, int):
            raise UnprocessableError(
                message=(
                    "For some reason count function returned not an integer."
                    f"Value: {value}"
                ),
            )

        return value
