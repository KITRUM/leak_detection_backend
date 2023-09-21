from sqlalchemy import Result, Select, select
from sqlalchemy.orm import joinedload

from src.infrastructure.database import (
    BaseRepository,
    SimulationDetectionsTable,
)
from src.infrastructure.errors import NotFoundError

from .models import Detection, DetectionUncommited

all = ("SimulationDetectionRepository",)


class SimulationDetectionsRepository(
    BaseRepository[SimulationDetectionsTable]
):
    schema_class = SimulationDetectionsTable

    async def get(self, id_: int) -> Detection:
        """Fetch the database record by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(joinedload(self.schema_class.anomaly_detection))
        )

        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return Detection.from_orm(schema)

    async def create(self, schema: DetectionUncommited) -> Detection:
        """Create a new record in database."""

        _schema: SimulationDetectionsTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return await self.get(id_=_schema.id)

    async def bulk_create(
        self, schemas: list[DetectionUncommited]
    ) -> list[Detection]:
        """Create new records in database."""

        _schemas: list[SimulationDetectionsTable] = await self._save_bulk(
            [self.schema_class(**schema.dict()) for schema in schemas]
        )

        return [(await self.get(id_=schema.id)) for schema in _schemas]
