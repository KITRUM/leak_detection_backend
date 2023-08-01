from src.domain.events import templates
from src.infrastructure.models import PublicModel


class EventPublic(PublicModel):
    id: int
    type: templates.EventType
    template_id: int
