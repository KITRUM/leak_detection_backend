from typing import AsyncGenerator

from sqlalchemy import Result, Select, desc, select
from sqlalchemy.orm import joinedload

from src.infrastructure.database import (
    BaseRepository,
    SensorsTable,
    TimeSeriesDataTable,
)
from src.infrastructure.errors import NotFoundError

from .models import Tsd, TsdInDb, TsdUncommited

all = ("TsdRepository",)


class TsdRepository(BaseRepository[TimeSeriesDataTable]):
    schema_class = TimeSeriesDataTable

    async def last(self) -> TsdInDb:
        """Fetch the time_series_data by id."""

        query: Select = select(self.schema_class).order_by(
            desc(self.schema_class.id)
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return TsdInDb.from_orm(schema)

    async def get(self, id_: int) -> Tsd:
        """Fetch the time_series_data by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(
                joinedload(self.schema_class.sensor).options(
                    joinedload(SensorsTable.template),
                    joinedload(SensorsTable.configuration),
                ),
            )
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return Tsd.from_orm(schema)

    async def create(self, schema: TsdUncommited) -> TsdInDb:
        """Create a new record in database."""

        _schema: TimeSeriesDataTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return TsdInDb.from_orm(_schema)

    async def by_sensor(self, sensor_id: int) -> AsyncGenerator[TsdInDb, None]:
        """Fetch all time series data by sensor from database.
        The sensor table is joined.
        """

        query: Select = select(self.schema_class).where(
            getattr(self.schema_class, "sensor_id") == sensor_id
        )

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield TsdInDb.from_orm(schema)

    async def fitler_last_by_sensor(
        self, sensor_id: int, id_: int, limit: int
    ) -> AsyncGenerator[TsdInDb, None]:
        """Fetch last values until the `id_` isntance in the database.
        If the limit is not set, then the anomaly detection window size
        setting is used.
        Used by the estimation component.
        """

        query: Select = (
            select(self.schema_class)
            .where(
                getattr(self.schema_class, "sensor_id") == sensor_id,
                getattr(self.schema_class, "id") <= id_,
            )
            .order_by(desc(self.schema_class.id))
            .limit(limit)
        )

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield TsdInDb.from_orm(schema)
