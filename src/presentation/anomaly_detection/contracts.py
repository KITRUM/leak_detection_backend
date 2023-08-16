from pydantic import Field

from src.domain.anomaly_detection import AnomalyDeviation
from src.domain.tsd import TsdFlat
from src.infrastructure.models import PublicModel


class AnomalyDetectionPublic(PublicModel):
    id: int
    value: AnomalyDeviation = Field(
        description="Define the enum of possible deviations"
    )
    time_series_data: TsdFlat = Field(
        description=(
            "Determine the time series data object "
            "that is related to this process"
        )
    )
    interactive_feedback_mode: bool = Field(
        description=(
            "Define if the interactive feedback was turned on "
            "for this time series data processing"
        )
    )
