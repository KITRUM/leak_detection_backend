from src.domain.tsd import TsdRaw
from src.infrastructure.models import PublicModel


class TsdPublic(TsdRaw, PublicModel):
    id: int
