from src.infrastructure.database.services.transaction import transaction

from ..models import EstimationSummary, EstimationSummaryUncommited
from ..repository import EstimationsSummariesRepository


@transaction
async def save(schema: EstimationSummaryUncommited) -> EstimationSummary:
    return await EstimationsSummariesRepository().create(schema)
