from src.domain.estimation import (
    EstimationsSummariesRepository,
    EstimationSummary,
)
from src.infrastructure.database import transaction


@transaction
async def get_historical_estimation_summaries(
    sensor_id: int,
) -> list[EstimationSummary]:
    """Get the historical estimation summaries for the given sensor."""

    return [
        EstimationSummary.from_orm(instance)
        async for instance in EstimationsSummariesRepository().by_sensor(
            sensor_id
        )
    ]
