from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Result, Select, asc, desc, select
from sqlalchemy.orm import joinedload

from src.domain.tsd.models import Tsd, TsdFlat, TsdUncommited
from src.infrastructure.database import (
    BaseRepository,
    SensorsTable,
    TimeSeriesDataTable,
)
from src.infrastructure.errors import NotFoundError

all = ("SensorsRepository",)


class TsdRepository(BaseRepository[TimeSeriesDataTable]):
    schema_class = TimeSeriesDataTable

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

    async def create(self, schema: TsdUncommited) -> TsdFlat:
        """Create a new record in database."""

        _schema: TimeSeriesDataTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return TsdFlat.from_orm(_schema)

    async def by_sensor(
        self,
        sensor_id: int,
        last_id: int | None = None,
        limit: int | None = None,
        timestamp_from: datetime | None = None,
        order_by_desc: bool = False,
    ) -> AsyncGenerator[TsdFlat, None]:
        """Fetch all time series data by sensor from database.
        The sensor table is joined.

        limit: int | None -- determines the max limit of results

        last_id: int | None -- determines the last TSD id that could
                 be in the results

        timestamp_from: datetime | None -- determines the timestamp which
                 used as a start time point

        order_by_desc: bool -- determines the order of results. Descending
                 is used by default.
        """

        query: Select = select(self.schema_class).where(
            getattr(self.schema_class, "sensor_id") == sensor_id
        )

        if order_by_desc:
            query = query.order_by(desc(self.schema_class.id))
        else:
            query = query.order_by(asc(self.schema_class.id))

        if last_id:
            query = query.where(
                getattr(self.schema_class, "id") <= last_id,
            )

        if limit:
            query = query.limit(limit)

        if timestamp_from:
            query = query.where(
                getattr(self.schema_class, "timestamp") > timestamp_from,
            )

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield TsdFlat.from_orm(schema)
