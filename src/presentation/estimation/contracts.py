from pydantic import Field

from src.domain.estimation import EstimationResult
from src.infrastructure.models import PublicModel


class EstimationSummaryPublic(PublicModel):
    id: int
    detection_id: int | None = None
    result: EstimationResult = Field(description="The main indicator")
