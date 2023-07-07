from typing import AsyncGenerator

from sqlalchemy import Result, Select, select
from sqlalchemy.orm import joinedload

from src.domain.anomaly_detection.models import (
    AnomalyDetection,
    AnomalyDetectionInDb,
    AnomalyDetectionUncommited,
)
from src.infrastructure.database import (
    AnomalyDetectionsTable,
    BaseRepository,
    TimeSeriesDataTable,
)
from src.infrastructure.errors import NotFoundError

all = ("AnomalyDetectionRepository",)


class AnomalyDetectionRepository(BaseRepository[AnomalyDetectionsTable]):
    schema_class = AnomalyDetectionsTable

    async def get(self, id_: int) -> AnomalyDetection:
        """Fetch the anomaly detection instance by id."""

        query: Select = (
            select(self.schema_class)
            .where(getattr(self.schema_class, "id") == id_)
            .options(joinedload(self.schema_class.time_series_data))
        )
        result: Result = await self._session.execute(query)

        if not (schema := result.scalars().one_or_none()):
            raise NotFoundError

        return AnomalyDetection.from_orm(schema)

    async def create(
        self, schema: AnomalyDetectionUncommited
    ) -> AnomalyDetectionInDb:
        """Create a new record in database."""

        _schema: AnomalyDetectionsTable = await self._save(
            self.schema_class(**schema.dict())
        )

        return AnomalyDetectionInDb.from_orm(_schema)

    async def by_sensor(
        self, sensor_id: int
    ) -> AsyncGenerator[AnomalyDetection, None]:
        """Fetch all anomaly detections for the sensor."""

        # .join(self.schema_class.time_series_data)
        query: Select = (
            select(self.schema_class)
            .join(self.schema_class.time_series_data)
            .options(
                joinedload(self.schema_class.time_series_data),
            )
            .where(getattr(TimeSeriesDataTable, "sensor_id") == sensor_id)
        )

        result: Result = await self._session.execute(query)

        if not (schemas := result.scalars().all()):
            raise NotFoundError

        for schema in schemas:
            yield AnomalyDetection.from_orm(schema)
