from enum import StrEnum, auto

from src.infrastructure.models import InternalModel

__all__ = (
    "EstimationResult",
    "EstimationSummaryUncommited",
    "EstimationSummary",
)


# TODO: Replace naming with the EstimationSummary
class EstimationResult(StrEnum):
    """Represent possible estimation result values."""

    CONFIRMED = auto()
    UNDEFINED = auto()
    EXTERNAL_CAUSE = auto()


class EstimationSummaryUncommited(InternalModel):
    result: EstimationResult
    sensor_id: int
    detection_id: int | None = None


class EstimationSummary(EstimationSummaryUncommited):
    id: int

    def __str__(self) -> str:
        return f"[id={self.id}] result: {self.result}."
