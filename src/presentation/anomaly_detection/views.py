from sqladmin import ModelView

from src.infrastructure.database import AnomalyDetectionsTable

__all__ = ("AnomalyDetectionsAdminView",)


class AnomalyDetectionsAdminView(ModelView, model=AnomalyDetectionsTable):
    name = "Anomaly detection"
    name_plural = "Anomaly detections"
    column_list = (
        "id",
        "value",
        "interactive_feedback_mode",
        "time_series_data",
    )
    column_searchable_list = (
        "value",
        "interactive_feedback_mode",
        "time_series_data",
    )
    column_sortable_list = (
        "id",
        "value",
        "interactive_feedback_mode",
        "time_series_data",
    )
    column_details_exclude_list = (
        "simulation_detection_rates",
        "time_series_data",
    )
    form_excluded_columns = (
        "simulation_detection_rates",
        "time_series_data",
    )
