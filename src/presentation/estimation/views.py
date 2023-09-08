from sqladmin import ModelView

from src.infrastructure.database import EstimationsSummariesTable

__all__ = ("EstimationAdminView",)


class EstimationAdminView(ModelView, model=EstimationsSummariesTable):
    name = "Estimation"
    name_plural = "Estimations"
    column_list = ("id", "result", "confidence", "sensor")
    column_searchable_list = ("result", "confidence", "sensor")
    column_sortable_list = ("id", "result", "sensor")
