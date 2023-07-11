from src.domain.anomaly_detection import AnomalyDetectionBase
from src.domain.tsd import TsdInDb
from src.infrastructure.models import PublicModel


class AnomalyDetectionPublic(AnomalyDetectionBase, PublicModel):
    id: int
    time_series_data: TsdInDb
