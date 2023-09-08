from sqladmin import ModelView

from src.infrastructure.database import SensorsEventsTable

__all__ = ("SensorEventsAdminView",)


class SensorEventsAdminView(ModelView, model=SensorsEventsTable):
    name = "Sensor Event"
    name_plural = "Sensor Events"
    column_list = ("id", "type", "sensor")
    column_searchable_list = ("type", "sensor")
    column_sortable_list = ("id", "type", "sensor")
