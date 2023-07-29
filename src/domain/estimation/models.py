from enum import StrEnum, auto

import numpy as np
from pydantic import validator

from src.infrastructure.models import InternalModel

__all__ = (
    "EstimationResult",
    "EstimationSummaryUncommited",
    "EstimationSummary",
)


class EstimationResult(StrEnum):
    """Represent possible estimation result values."""

    CONFIRMED = auto()
    ABSENT = auto()
    EXTERNAL_CAUSE = auto()
    SENSOR_NOT_AVAILABLE = auto()


class _EstimationSummaryBase(InternalModel):
    result: EstimationResult
    leakage_index: int


class EstimationSummaryUncommited(_EstimationSummaryBase):
    simulation_detection_rate_ids: str
    confidence: float

    @validator("simulation_detection_rate_ids", pre=True)
    def convert_from_flat(cls, value: list[int]) -> str:
        """Convert into a flat data type beacuse
        of the SQLite database types limitation.
        """

        return ",".join(str(el) for el in value)


class EstimationSummary(_EstimationSummaryBase):
    id: int
    confidence: np.float64
    simulation_detection_rate_ids: list[int]

    @validator("simulation_detection_rate_ids", pre=True)
    def convert_from_flat(cls, value: str) -> list[int]:
        """Convert flat rate ids that are storing as string
        in the SQLite database into the list of regular integers.
        """

        return [int(el) for el in value.strip(",")]

    @validator("confidence", pre=True)
    def convert_numpy_types(cls, value: float) -> np.float64:
        return np.float64(value)
