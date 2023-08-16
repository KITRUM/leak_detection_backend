from sqlalchemy import Result, Select, select
from sqlalchemy.orm import joinedload

from src.domain.simulation.models import (
    SimulationDetectionRateFlat,
    SimulationDetectionRateUncommited,
)
from src.infrastructure.database import (
    BaseRepository,
    SimulationDetectionRatesTable,
)
from src.infrastructure.errors import NotFoundError

all = ("SimulationDetectionRatesRepository",)


class SimulationDetectionRatesRepository(
    BaseRepository[SimulationDetectionRatesTable]
):
    schema_class = SimulationDetectionRatesTable

    async def get(self, id_: int) -> SimulationDetectionRateFlat:
        """Fetch the database record by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(joinedload(self.schema_class.anomaly_detection))
        )

        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return SimulationDetectionRateFlat.from_orm(schema)

    async def create(
        self, schema: SimulationDetectionRateUncommited
    ) -> SimulationDetectionRateFlat:
        """Create a new record in database."""

        _schema: SimulationDetectionRatesTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return await self.get(id_=_schema.id)
