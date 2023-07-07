import random

from sqlalchemy import delete

from src.application.database import transaction
from src.domain.anomaly_detection.constants import AnomalyDeviation
from src.domain.anomaly_detection.models import (
    AnomalyDetection,
    AnomalyDetectionUncommited,
)
from src.domain.anomaly_detection.repository import AnomalyDetectionRepository
from src.domain.tsd import Tsd
from src.infrastructure.database import AnomalyDetectionsTable


@transaction
async def save_anomaly_detection(
    schema: AnomalyDetectionUncommited,
) -> AnomalyDetection:
    repository = AnomalyDetectionRepository()
    instance = await repository.create(schema)

    return await repository.get(instance.id)


@transaction
async def delete_all():
    """This function is used by the startup hook if debug mode is on."""

    await AnomalyDetectionRepository().execute(delete(AnomalyDetectionsTable))


def _get_deviation(tsd: Tsd) -> AnomalyDeviation:
    return random.choice(
        [
            AnomalyDeviation.CRITICAL,
            AnomalyDeviation.WARNING,
            AnomalyDeviation.OK,
        ]
    )


def process(tsd: Tsd) -> AnomalyDetectionUncommited:
    create_schema = AnomalyDetectionUncommited(
        value=_get_deviation(tsd), time_series_data_id=tsd.id
    )

    return create_schema
