from datetime import datetime

from src.infrastructure.models import PublicModel


class TsdPublic(PublicModel):
    id: int
    ppmv: float
    timestamp: datetime
