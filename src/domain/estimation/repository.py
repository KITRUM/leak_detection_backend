from typing import AsyncGenerator

from sqlalchemy import Result, Select, select

from src.domain.estimation.models import (
    EstimationSummary,
    EstimationSummaryUncommited,
)
from src.infrastructure.database import (
    BaseRepository,
    EstimationsSummariesTable,
)
from src.infrastructure.errors import NotFoundError

all = ("EstimationsSummariesRepository",)


class EstimationsSummariesRepository(
    BaseRepository[EstimationsSummariesTable]
):
    schema_class = EstimationsSummariesTable

    async def get(self, id_: int) -> EstimationSummary:
        """Fetch the database record by id."""

        query: Select = select(self.schema_class).where(
            getattr(self.schema_class, "id") == id_
        )

        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return EstimationSummary.from_orm(schema)

    async def create(
        self, schema: EstimationSummaryUncommited
    ) -> EstimationSummary:
        """Create a new record in database."""

        _schema: EstimationsSummariesTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return EstimationSummary.from_orm(_schema)

    async def by_sensor(
        self, sensor_id: int
    ) -> AsyncGenerator[EstimationSummary, None]:
        """Fetch all anomaly detections for the sensor."""

        query: Select = select(self.schema_class).where(
            getattr(self.schema_class, "sensor_id") == sensor_id
        )

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield EstimationSummary.from_orm(schema)
