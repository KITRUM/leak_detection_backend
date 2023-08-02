from sqlalchemy import delete

from src.infrastructure.database import EstimationsSummariesTable
from src.infrastructure.database.services.transaction import transaction

from ..models import EstimationSummary, EstimationSummaryUncommited
from ..repository import EstimationsSummariesRepository


@transaction
async def save(schema: EstimationSummaryUncommited) -> EstimationSummary:
    return await EstimationsSummariesRepository().create(schema)


@transaction
async def delete_all():
    """This function is used by the startup hook if debug mode is on."""

    await EstimationsSummariesRepository().execute(
        delete(EstimationsSummariesTable)
    )


@transaction
async def get_historical_data(sensor_id: int) -> list[EstimationSummary]:
    """Get the historical data."""

    return [
        instance
        async for instance in EstimationsSummariesRepository().by_sensor(
            sensor_id
        )
    ]