from sqladmin import ModelView

from src.infrastructure.database import TemplatesTable

__all__ = ("TemplatesAdminView",)


class TemplatesAdminView(ModelView, model=TemplatesTable):
    name = "Template"
    name_plural = "Templates"
    column_list = ("id", "name", "angle_from_north", "field_id", "sensors")
    column_searchable_list = (
        "name",
        "angle_from_north",
        "field_id",
        "sensors",
    )
    column_sortable_list = (
        "id",
        "name",
        "angle_from_north",
        "field_id",
        "sensors",
    )
