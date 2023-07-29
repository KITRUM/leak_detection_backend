from typing import Any

from pydantic import Field, validator

from src.domain.estimation import EstimationResult
from src.infrastructure.models import PublicModel


class EstimationSummaryPublic(PublicModel):
    id: int
    simulation_detection_rates: list[float]
    confidence: float
    result: EstimationResult = Field(description="The main indicator")

    @validator("confidence", pre=True)
    def convert_into_flat_type(cls, value: Any) -> float:
        return float(value)
