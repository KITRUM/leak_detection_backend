from enum import StrEnum, auto

import numpy as np

from src.infrastructure.models import InternalModel


class EstimationResult(StrEnum):
    """Represent possible estimation result values."""

    CONFIRMED = auto()
    ABSENT = auto()
    EXTERNAL_CAUSE = auto()
    SENSOR_NOT_AVAILABLE = auto()


class _EstimationSummaryBase(InternalModel):
    result: EstimationResult
    confidence: np.float64


class EstimationSummary(_EstimationSummaryBase):
    """Represents the estimation result with attached data."""

    leakage_index: int


class EstimationSummaryUncommited(_EstimationSummaryBase):
    leakage: dict
