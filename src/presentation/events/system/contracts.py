from src.domain.events import system
from src.infrastructure.models import PublicModel


class EventPublic(PublicModel):
    id: int
    message: str
    type: system.EventType
