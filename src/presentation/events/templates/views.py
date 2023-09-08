from sqladmin import ModelView

from src.infrastructure.database import TemplatesEventsTable

__all__ = ("TemplateEventsAdminView",)


class TemplateEventsAdminView(ModelView, model=TemplatesEventsTable):
    name = "Template Event"
    name_plural = "Template Events"
    column_list = ("id", "type", "template")
    column_searchable_list = ("type", "template")
    column_sortable_list = ("id", "type", "template")
