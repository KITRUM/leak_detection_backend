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

        rate_ids_as_string = ",".join(
            (str(el) for el in schema.simulation_detection_rate_ids)
        )
        payload = schema.dict() | {
            "simulation_detection_rate_ids": rate_ids_as_string
        }

        _schema: EstimationsSummariesTable = await self._save(
            self.schema_class(**payload)
        )

        return await self.get(id_=_schema.id)
