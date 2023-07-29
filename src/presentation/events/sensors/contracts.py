from src.domain.events import sensors
from src.infrastructure.models import PublicModel


class EventPublic(PublicModel):
    id: int
    type: sensors.EventType
    sensor_id: int
